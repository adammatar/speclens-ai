#!/usr/bin/env bash
# Reset the default SpecLens workspace into a complete deterministic demo:
# two synthetic versions, extraction, comparison, and (when available) eval report.
# Stub backends only — no paid providers. Idempotent local/demo use.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/infra/compose.yaml}"
API_URL="${API_URL:-http://127.0.0.1:8001}"
AUTH_HEADER="${AUTH_HEADER:-Authorization: Bearer speclens-local-dev-key}"
WORKSPACE_ID="00000000-0000-4000-8000-000000000001"
FIXTURE_V1="$ROOT/services/api/tests/fixtures/sample.md"
FIXTURE_V2="$ROOT/demos/demo-sample-spec-v2.md"
SEED_V1="$(mktemp /tmp/speclens-demo-v1-XXXXXX.md)"
SEED_V2="$(mktemp /tmp/speclens-demo-v2-XXXXXX.md)"
TIMEOUT_SECS="${DEMO_JOB_TIMEOUT_SECS:-90}"

cleanup() {
  rm -f "$SEED_V1" "$SEED_V2"
}
trap cleanup EXIT

log() { printf '%s\n' "$*"; }
die() { printf 'demo_reset ERROR: %s\n' "$*" >&2; exit 1; }

wait_json_status() {
  # wait_json_status <url> <json_path_status_field> <label>
  local url="$1"
  local field="${2:-status}"
  local label="${3:-job}"
  local status=""
  local body=""
  local i
  for i in $(seq 1 "$TIMEOUT_SECS"); do
    body=$(curl -sf -H "$AUTH_HEADER" "$url") || die "$label: failed to fetch $url"
    status=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])" "$body" "$field")
    if [ "$status" = "succeeded" ] || [ "$status" = "failed" ] || [ "$status" = "ready" ]; then
      printf '%s\n' "$status"
      return 0
    fi
    sleep 1
  done
  die "$label timed out after ${TIMEOUT_SECS}s (last status=$status)"
}

wait_embeddings() {
  local version_id="$1"
  local label="$2"
  local count=0
  local i
  for i in $(seq 1 "$TIMEOUT_SECS"); do
    count=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U speclens -d speclens -Atc \
      "select count(*) from chunk_embeddings where document_version_id='${version_id}'" 2>/dev/null || echo 0)
    if [ "${count:-0}" -gt 0 ]; then
      log "  embeddings ready for $label ($count)"
      return 0
    fi
    sleep 1
  done
  die "$label: embeddings not ready after ${TIMEOUT_SECS}s"
}

log "Demo reset against $API_URL (compose=$COMPOSE_FILE)"
curl -sf "$API_URL/api/v1/ready" >/dev/null || die "API not ready at $API_URL"

# Ensure local bootstrap key is active (migrations deactivate it for production safety).
docker compose -f "$COMPOSE_FILE" exec -T api python -m app.cli bootstrap-local >/dev/null \
  || die "bootstrap-local failed"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U speclens -d speclens -v ON_ERROR_STOP=1 <<SQL
DELETE FROM documents WHERE workspace_id = '$WORKSPACE_ID';
DELETE FROM conversations WHERE workspace_id = '$WORKSPACE_ID';
DELETE FROM audit_events WHERE workspace_id = '$WORKSPACE_ID';
SQL

docker compose -f "$COMPOSE_FILE" exec -T api \
  sh -c "rm -rf /data/storage/workspaces/${WORKSPACE_ID} || true"

# --- Version 1 ---
UNIQUE="$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
{
  cat "$FIXTURE_V1"
  printf '\n\n<!-- demo-seed-v1 %s -->\n' "$UNIQUE"
} > "$SEED_V1"

UPLOAD=$(curl -sf -X POST "$API_URL/api/v1/documents/upload" \
  -H "$AUTH_HEADER" \
  -F "file=@${SEED_V1};type=text/markdown" \
  -F "title=Demo Sample Spec") || die "upload v1 failed"
log "$UPLOAD"
DOC_ID=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['document_id'])" "$UPLOAD")
VER1=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['document_version_id'])" "$UPLOAD")
JOB1=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$UPLOAD")

STATUS=$(wait_json_status "$API_URL/api/v1/documents/jobs/${JOB1}" status "ingest v1")
[ "$STATUS" = "succeeded" ] || die "ingest v1 failed: $STATUS"
wait_embeddings "$VER1" "v1"

EXT1=$(curl -sf -H "$AUTH_HEADER" -X POST \
  "$API_URL/api/v1/documents/versions/${VER1}/extractions") || die "start extraction v1 failed"
EJOB1=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$EXT1")
STATUS=$(wait_json_status "$API_URL/api/v1/extractions/${EJOB1}" status "extract v1")
[ "$STATUS" = "succeeded" ] || die "extract v1 failed: $STATUS"
REQS=$(curl -sf -H "$AUTH_HEADER" \
  "$API_URL/api/v1/requirements?document_version_id=${VER1}")
python3 -c "import json,sys; rows=json.loads(sys.argv[1]); assert rows, 'no requirements extracted for v1'" "$REQS"
log "  requirements v1: $(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])))" "$REQS")"

# --- Version 2 (deterministic synthetic changes) ---
if [ -f "$FIXTURE_V2" ]; then
  {
    cat "$FIXTURE_V2"
    printf '\n\n<!-- demo-seed-v2 %s -->\n' "$UNIQUE"
  } > "$SEED_V2"
else
  # Fallback: mutate v1 in-script if fixture missing
  {
    sed \
      -e 's/preserve heading paths on every chunk/preserve heading paths on every chunk for navigation/' \
      -e 's/roughly six hundred to nine hundred tokens/exactly seven hundred tokens/' \
      "$FIXTURE_V1"
    printf '\n\n### Audit\n\nThe system shall emit structured audit events for rejected uploads.\n'
    printf '\n<!-- demo-seed-v2 %s -->\n' "$UNIQUE"
  } > "$SEED_V2"
fi

UP2=$(curl -sf -X POST "$API_URL/api/v1/documents/${DOC_ID}/versions" \
  -H "$AUTH_HEADER" \
  -F "file=@${SEED_V2};type=text/markdown") || die "upload v2 failed"
VER2=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['document_version_id'])" "$UP2")
JOB2=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$UP2")
STATUS=$(wait_json_status "$API_URL/api/v1/documents/jobs/${JOB2}" status "ingest v2")
[ "$STATUS" = "succeeded" ] || die "ingest v2 failed: $STATUS"
wait_embeddings "$VER2" "v2"

EXT2=$(curl -sf -H "$AUTH_HEADER" -X POST \
  "$API_URL/api/v1/documents/versions/${VER2}/extractions") || die "start extraction v2 failed"
EJOB2=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$EXT2")
STATUS=$(wait_json_status "$API_URL/api/v1/extractions/${EJOB2}" status "extract v2")
[ "$STATUS" = "succeeded" ] || die "extract v2 failed: $STATUS"

CMP=$(curl -sf -X POST "$API_URL/api/v1/comparisons" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d "{\"base_document_version_id\":\"${VER1}\",\"target_document_version_id\":\"${VER2}\"}") \
  || die "start comparison failed"
CJOB=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$CMP")
STATUS=$(wait_json_status "$API_URL/api/v1/comparisons/${CJOB}" status "compare")
[ "$STATUS" = "succeeded" ] || die "compare failed: $STATUS"
CJ=$(curl -sf -H "$AUTH_HEADER" "$API_URL/api/v1/comparisons/${CJOB}")
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d.get('changes'), 'comparison produced no changes'" "$CJ"
log "  comparison changes: $(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['changes']))" "$CJ")"

# Ensure a current stub evaluation report exists for the Evaluation dashboard.
if [ ! -f "$ROOT/artifacts/eval/report.json" ] && [ ! -f "$ROOT/evals/reports/latest.json" ]; then
  log "Generating stub evaluation report (make eval)…"
  (cd "$ROOT" && make eval) || die "make eval failed; Evaluation dashboard needs a report"
else
  log "Evaluation report already present under artifacts/eval or evals/reports"
fi

log "Demo workspace ready:"
log "  document_id=$DOC_ID"
log "  version_v1=$VER1"
log "  version_v2=$VER2"
log "  comparison_job=$CJOB"
log "Demo Sample Spec is populated with requirements + compare changes (synthetic/stub only)."
