#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export IMPERIALAX_ENV="production"

if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
  echo ".env.local loaded" >&2
fi

if [[ -z "${IMPERIALAX_ADMIN_TOKEN:-}" ]]; then
  token_file=".omx/state/imperialax-admin-token.txt"
  if [[ ! -r "${token_file}" ]]; then
    echo "IMPERIALAX_ADMIN_TOKEN is unset and ${token_file} is not readable." >&2
    exit 1
  fi
  export IMPERIALAX_ADMIN_TOKEN="$(<"${token_file}")"
fi
if [[ -z "${IMPERIALAX_ADMIN_TOKEN}" ]]; then
  echo "IMPERIALAX_ADMIN_TOKEN must not be empty." >&2
  exit 1
fi
echo "IMPERIALAX_ADMIN_TOKEN configured length: ${#IMPERIALAX_ADMIN_TOKEN}" >&2
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY configured length: ${#OPENAI_API_KEY}" >&2
else
  echo "OPENAI_API_KEY is not configured; RAG will use local fallback answers." >&2
fi

exec .venv/bin/uvicorn src.backend.dd_laminate_app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1
