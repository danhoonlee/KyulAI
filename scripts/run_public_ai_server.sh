#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export LUVELOX_ADMIN_TOKEN="${LUVELOX_ADMIN_TOKEN:-$(cat .omx/state/luvelox-admin-token.txt)}"
echo "LUVELOX_ADMIN_TOKEN configured length: ${#LUVELOX_ADMIN_TOKEN}" >&2

exec .venv/bin/uvicorn src.backend.dd_laminate_app:app --host 0.0.0.0 --port 8000
