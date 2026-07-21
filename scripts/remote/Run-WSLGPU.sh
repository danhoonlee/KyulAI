#!/usr/bin/env bash
set -euo pipefail

HOST="${KYULAI_WSL_HOST:-user@100.65.153.56}"
KEY="${KYULAI_WSL_KEY:-$HOME/.ssh/kyulai_wsl_gpu_codex}"
PROJECT_DIR="${KYULAI_WSL_PROJECT:-~/projects/KyulAI}"

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 '<command to run inside ~/projects/KyulAI>'" >&2
  echo "Example: $0 'python --version && python scripts/dd_response_distillation_train.py --help'" >&2
  exit 2
fi

REMOTE_CMD="$*"
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST" "set -euo pipefail; cd $PROJECT_DIR; source .venv/bin/activate; $REMOTE_CMD"
