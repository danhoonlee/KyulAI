#!/usr/bin/env bash
set -euo pipefail

umask 077

KYULAI_ROOT="${KYULAI_ROOT:-$HOME/projects/KyulAI}"
NANGMAN_ROOT="${NANGMAN_ROOT:-$HOME/projects/nangman-rag}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/c/Users/user/ImperialAX-Backups}"
BACKUP_RETENTION="${BACKUP_RETENTION:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="imperialax-serving-${STAMP}.tar.gz"
LOCK_DIR="${XDG_RUNTIME_DIR:-/tmp}/imperialax-serving-backup.lock"
STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/imperialax-serving-backup.XXXXXX")"
LOCK_ACQUIRED=0

cleanup() {
  rm -rf "${STAGING_DIR}"
  if [[ "${LOCK_ACQUIRED}" == "1" ]]; then
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another ImperialAX serving backup is already running." >&2
  exit 0
fi
LOCK_ACQUIRED=1

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Required backup source is missing: $1" >&2
    exit 1
  fi
}

copy_private_file() {
  local source="$1"
  local destination="$2"
  require_file "${source}"
  mkdir -p "$(dirname "${destination}")"
  install -m 600 "${source}" "${destination}"
}

snapshot_sqlite() {
  local source="$1"
  local destination="$2"
  require_file "${source}"
  mkdir -p "$(dirname "${destination}")"
  python3 - "${source}" "${destination}" <<'PY'
from pathlib import Path
import sqlite3
import sys

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()

with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
    with sqlite3.connect(destination) as destination_db:
        source_db.backup(destination_db)
        result = destination_db.execute("PRAGMA integrity_check").fetchone()

if not result or result[0] != "ok":
    raise SystemExit(f"SQLite integrity check failed for {source}: {result}")

destination.chmod(0o600)
PY
}

snapshot_jsonl() {
  local source="$1"
  local destination="$2"
  require_file "${source}"
  mkdir -p "$(dirname "${destination}")"
  python3 - "${source}" "${destination}" <<'PY'
from pathlib import Path
import json
import sys
import time

source = Path(sys.argv[1])
destination = Path(sys.argv[2])

for attempt in range(3):
    payload = source.read_bytes()
    try:
        text = payload.decode("utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.strip():
                json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        if attempt == 2:
            raise
        time.sleep(0.25)
        continue
    destination.write_bytes(payload)
    destination.chmod(0o600)
    break
PY
}

mkdir -p "${STAGING_DIR}/kyulai/runtime/wedding"
mkdir -p "${STAGING_DIR}/kyulai/data"
mkdir -p "${STAGING_DIR}/kyulai/config"
mkdir -p "${STAGING_DIR}/nangman/data"
mkdir -p "${STAGING_DIR}/nangman/config"
mkdir -p "${STAGING_DIR}/host/cloudflared"
mkdir -p "${STAGING_DIR}/host/systemd-user"

snapshot_jsonl \
  "${KYULAI_ROOT}/runtime/wedding/rsvp-submissions.jsonl" \
  "${STAGING_DIR}/kyulai/runtime/wedding/rsvp-submissions.jsonl"
copy_private_file \
  "${KYULAI_ROOT}/runtime/wedding/admin-token.txt" \
  "${STAGING_DIR}/kyulai/runtime/wedding/admin-token.txt"
copy_private_file \
  "${KYULAI_ROOT}/.omx/state/imperialax-admin-token.txt" \
  "${STAGING_DIR}/kyulai/config/imperialax-admin-token.txt"
copy_private_file \
  "${KYULAI_ROOT}/.env.local" \
  "${STAGING_DIR}/kyulai/config/env.local"

for auth_db in "${KYULAI_ROOT}"/data/*_auth.sqlite3; do
  [[ -e "${auth_db}" ]] || continue
  snapshot_sqlite "${auth_db}" "${STAGING_DIR}/kyulai/data/$(basename "${auth_db}")"
done

snapshot_sqlite \
  "${NANGMAN_ROOT}/data/romance.db" \
  "${STAGING_DIR}/nangman/data/romance.db"
copy_private_file \
  "${NANGMAN_ROOT}/.env" \
  "${STAGING_DIR}/nangman/config/env"

if [[ -d "${HOME}/.cloudflared" ]]; then
  while IFS= read -r -d '' source; do
    install -m 600 "${source}" "${STAGING_DIR}/host/cloudflared/$(basename "${source}")"
  done < <(find "${HOME}/.cloudflared" -maxdepth 1 -type f \
    \( -name '*.json' -o -name '*.pem' -o -name '*.crt' \) -print0)
fi

if [[ -d "${HOME}/.config/systemd/user" ]]; then
  while IFS= read -r -d '' source; do
    install -m 600 "${source}" "${STAGING_DIR}/host/systemd-user/$(basename "${source}")"
  done < <(find "${HOME}/.config/systemd/user" -maxdepth 1 -type f \
    \( -name '*.service' -o -name '*.timer' \) -print0)
fi

cat > "${STAGING_DIR}/MANIFEST.txt" <<EOF
created_at=$(date --iso-8601=seconds)
hostname=$(hostname)
kyulai_root=${KYULAI_ROOT}
nangman_root=${NANGMAN_ROOT}
backup_root=${BACKUP_ROOT}
retention=${BACKUP_RETENTION}
EOF

mkdir -p "${BACKUP_ROOT}"
PARTIAL_ARCHIVE="${BACKUP_ROOT}/.${ARCHIVE_NAME}.partial"
FINAL_ARCHIVE="${BACKUP_ROOT}/${ARCHIVE_NAME}"

tar -C "${STAGING_DIR}" -czf "${PARTIAL_ARCHIVE}" .
tar -tzf "${PARTIAL_ARCHIVE}" >/dev/null
mv "${PARTIAL_ARCHIVE}" "${FINAL_ARCHIVE}"
sha256sum "${FINAL_ARCHIVE}" > "${FINAL_ARCHIVE}.sha256"

python3 - "${BACKUP_ROOT}" "${BACKUP_RETENTION}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
retention = int(sys.argv[2])
if retention < 1:
    raise SystemExit("BACKUP_RETENTION must be at least 1")

archives = sorted(
    root.glob("imperialax-serving-*.tar.gz"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
for archive in archives[retention:]:
    checksum = Path(f"{archive}.sha256")
    archive.unlink(missing_ok=True)
    checksum.unlink(missing_ok=True)
PY

echo "Backup complete: ${FINAL_ARCHIVE}"
