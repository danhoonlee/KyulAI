#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
  echo ".env.local loaded" >&2
fi

if [[ -z "${IMPERIALAX_ADMIN_TOKEN:-}" ]]; then
  if [[ -n "${IMPERIALAX_ADMIN_TOKEN:-}" ]]; then
    export IMPERIALAX_ADMIN_TOKEN="${IMPERIALAX_ADMIN_TOKEN}"
  else
    export IMPERIALAX_ADMIN_TOKEN="$(cat .omx/state/imperialax-admin-token.txt)"
  fi
fi
echo "IMPERIALAX_ADMIN_TOKEN configured length: ${#IMPERIALAX_ADMIN_TOKEN}" >&2
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY configured length: ${#OPENAI_API_KEY}" >&2
else
  echo "OPENAI_API_KEY is not configured; RAG will use local fallback answers." >&2
fi

exec .venv/bin/uvicorn src.backend.dd_laminate_app:app --host 0.0.0.0 --port 8000
