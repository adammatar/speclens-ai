#!/usr/bin/env bash
# CI-safe backup/restore verification using an isolated temporary database.
# Does not destroy the developer Compose database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/infra/compose.yaml")
TMP_DIR="${TMPDIR:-/tmp}/speclens-backup-verify-$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "==> Ensuring local Postgres is up"
"${COMPOSE[@]}" up -d postgres
for _ in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T postgres pg_isready -U speclens -d speclens >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

VERIFY_DB="speclens_backup_verify"
echo "==> Creating isolated database ${VERIFY_DB}"
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d speclens -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${VERIFY_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${VERIFY_DB};
CREATE DATABASE ${VERIFY_DB} OWNER speclens;
SQL

echo "==> Installing pgvector + schema into verify DB"
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d "$VERIFY_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
# Dump schema+data from primary, restore into verify DB (synthetic-safe).
"${COMPOSE[@]}" exec -T postgres pg_dump -U speclens --schema-only speclens > "$TMP_DIR/schema.sql"
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d "$VERIFY_DB" -v ON_ERROR_STOP=1 < "$TMP_DIR/schema.sql"

# Seed a synthetic document row via SQL (no confidential content).
DOC_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
WS_ID="00000000-0000-4000-8000-000000000001"
SHA="$(python3 - <<'PY'
import hashlib
print(hashlib.sha256(b"synthetic backup verify").hexdigest())
PY
)"

"${COMPOSE[@]}" exec -T postgres psql -U speclens -d "$VERIFY_DB" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO workspaces (id, name)
VALUES ('${WS_ID}', 'default')
ON CONFLICT (id) DO NOTHING;
INSERT INTO documents (id, workspace_id, title)
VALUES ('${DOC_ID}', '${WS_ID}', 'synthetic-backup-verify');
INSERT INTO document_versions (
  id, document_id, workspace_id, version_number, filename, content_type,
  byte_size, sha256, storage_key, status
) VALUES (
  '${DOC_ID}', '${DOC_ID}', '${WS_ID}', 1, 'backup-verify.md', 'text/markdown',
  24, '${SHA}', 'verify/${DOC_ID}.md', 'ready'
);
SQL

echo "==> Logical backup of verify DB"
"${COMPOSE[@]}" exec -T postgres pg_dump -U speclens "$VERIFY_DB" > "$TMP_DIR/backup.sql"

echo "==> Drop and restore verify DB from backup"
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d speclens -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${VERIFY_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${VERIFY_DB};
CREATE DATABASE ${VERIFY_DB} OWNER speclens;
SQL
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d "$VERIFY_DB" -v ON_ERROR_STOP=1 < "$TMP_DIR/backup.sql"

COUNT="$("${COMPOSE[@]}" exec -T postgres psql -U speclens -d "$VERIFY_DB" -Atc "SELECT count(*) FROM documents WHERE id = '${DOC_ID}';")"
if [[ "$COUNT" != "1" ]]; then
  echo "Restore verification failed: expected document row" >&2
  exit 1
fi

echo "==> Cleaning isolated verify database"
"${COMPOSE[@]}" exec -T postgres psql -U speclens -d speclens -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${VERIFY_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${VERIFY_DB};
SQL

echo "Backup/restore verification passed (isolated DB; developer data untouched)."
