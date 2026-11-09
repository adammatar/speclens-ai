#!/usr/bin/env bash
# Reset the default SpecLens workspace for local/demo use.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/infra/compose.yaml}"
API_URL="${API_URL:-http://127.0.0.1:8000}"
AUTH_HEADER="${AUTH_HEADER:-Authorization: Bearer speclens-local-dev-key}"
WORKSPACE_ID="00000000-0000-4000-8000-000000000001"
FIXTURE="$ROOT/services/api/tests/fixtures/sample.md"

echo "Demo reset against $API_URL (compose=$COMPOSE_FILE)"

curl -sf "$API_URL/api/v1/ready" >/dev/null

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U speclens -d speclens -v ON_ERROR_STOP=1 <<SQL
DELETE FROM documents WHERE workspace_id = '$WORKSPACE_ID';
DELETE FROM conversations WHERE workspace_id = '$WORKSPACE_ID';
DELETE FROM audit_events WHERE workspace_id = '$WORKSPACE_ID';
SQL

# Clear object-store bytes via the API container (volume ownership is root in Compose).
docker compose -f "$COMPOSE_FILE" exec -T api \
  sh -c "rm -rf /data/storage/workspaces/${WORKSPACE_ID} || true"

UPLOAD=$(curl -sf -X POST "$API_URL/api/v1/documents/upload" \
  -H "$AUTH_HEADER" \
  -F "file=@${FIXTURE};type=text/markdown" \
  -F "title=Demo Sample Spec")
echo "$UPLOAD"
JOB_ID=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['job_id'])" "$UPLOAD")

for i in $(seq 1 40); do
  JOB=$(curl -sf -H "$AUTH_HEADER" "$API_URL/api/v1/documents/jobs/${JOB_ID}")
  STATUS=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['status'])" "$JOB")
  if [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 1
done

echo "Ingest status: $STATUS"
test "$STATUS" = "succeeded"
echo "Demo workspace re-seeded."
