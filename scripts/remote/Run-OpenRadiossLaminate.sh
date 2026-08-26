#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 <abaqus.inp> [run-name]" >&2
  exit 2
fi

INPUT_FILE="$1"
RUN_NAME="${2:-$(basename "${INPUT_FILE%.inp}" | tr -cs 'A-Za-z0-9_.-' '_')}"
HOST="${KYULAI_WSL_HOST:-user@100.65.153.56}"
KEY="${KYULAI_WSL_KEY:-${HOME}/.ssh/kyulai_wsl_gpu_codex}"
THREADS="${OPENRADIOSS_THREADS:-8}"
RUN_TIME="${OPENRADIOSS_RUN_TIME:-0.005}"
OUTPUT_INTERVAL="${OPENRADIOSS_OUTPUT_INTERVAL:-}"
ANALYSIS_MODE="${OPENRADIOSS_ANALYSIS_MODE:-explicit}"
SHELL_FORMULATION="${OPENRADIOSS_SHELL_FORMULATION:-}"
IMPLICIT_NONLINEAR_METHOD="${OPENRADIOSS_IMPLICIT_NONLINEAR_METHOD:-2}"
INITIAL_GEOMETRY_Z_SCALE="${OPENRADIOSS_INITIAL_GEOMETRY_Z_SCALE:-1}"
HISTORY_ONLY="${OPENRADIOSS_HISTORY_ONLY:-0}"
RELEASE="${OPENRADIOSS_RELEASE:-latest-20260728}"
MUMPS_ENGINE="${OPENRADIOSS_MUMPS_ENGINE:-/home/user/projects/OpenRadioss-mumps-src/exec/engine_linux64_gf_ompi}"
MPI_ROOT="${OPENRADIOSS_MPI_ROOT:-/home/user/.local/opt/openmpi-conda}"
REMOTE_ROOT="${OPENRADIOSS_REMOTE_ROOT:-/home/user/projects/KyulAI/runs/openradioss}"
RUN_ID="${OPENRADIOSS_RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
REMOTE_DIR="${REMOTE_ROOT}/${RUN_NAME}_${RUN_ID}"
LOCAL_DIR=".tmp/openradioss/${RUN_NAME}_${RUN_ID}"

if [ ! -f "$INPUT_FILE" ]; then
  echo "Input file not found: $INPUT_FILE" >&2
  exit 2
fi

mkdir -p "$LOCAL_DIR"
CONVERTER_ARGS=(
  "$INPUT_FILE"
  --output-dir "$LOCAL_DIR"
  --run-name "$RUN_NAME"
  --analysis-mode "$ANALYSIS_MODE"
  --implicit-nonlinear-method "$IMPLICIT_NONLINEAR_METHOD"
  --initial-geometry-z-scale "$INITIAL_GEOMETRY_Z_SCALE"
  --run-time "$RUN_TIME"
)
if [ -n "$SHELL_FORMULATION" ]; then
  CONVERTER_ARGS+=(--shell-formulation "$SHELL_FORMULATION")
fi
if [ -n "$OUTPUT_INTERVAL" ]; then
  CONVERTER_ARGS+=(--output-interval "$OUTPUT_INTERVAL")
fi
if [ "$HISTORY_ONLY" = 1 ]; then
  CONVERTER_ARGS+=(--history-only)
fi
.venv/bin/python scripts/inp2rad_laminate.py "${CONVERTER_ARGS[@]}"

ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST" "mkdir -p '$REMOTE_DIR'"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new \
  "$LOCAL_DIR/${RUN_NAME}_0000.rad" \
  "$LOCAL_DIR/${RUN_NAME}_0001.rad" \
  "$LOCAL_DIR/${RUN_NAME}_conversion.json" \
  "$HOST:$REMOTE_DIR/"

ssh -tt -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST" "bash -lc '
  set -euo pipefail
  cd \"$REMOTE_DIR\"
  openradioss_root=/home/user/.local/opt/openradioss/$RELEASE/OpenRadioss
  export OPENRADIOSS_PATH=\"\$openradioss_root\"
  export RAD_CFG_PATH=\"\$openradioss_root/hm_cfg_files\"
  export RAD_H3D_PATH=\"\$openradioss_root/extlib/h3d/lib/linux64\"
  export LD_LIBRARY_PATH=\"\$openradioss_root/extlib/hm_reader/linux64:\$openradioss_root/extlib/h3d/lib/linux64:\${LD_LIBRARY_PATH:-}\"
  export OMP_STACKSIZE=400m
  \"\$openradioss_root/exec/starter_linux64_gf\" -i \"${RUN_NAME}_0000.rad\" -nspmd 1 -nt \"$THREADS\"
  if [ \"$ANALYSIS_MODE\" = implicit ]; then
    export PATH=\"$MPI_ROOT/bin:\$PATH\"
    export LD_LIBRARY_PATH=\"$MPI_ROOT/lib:\$LD_LIBRARY_PATH\"
    \"$MPI_ROOT/bin/mpirun\" -np 1 \"$MUMPS_ENGINE\" -i \"${RUN_NAME}_0001.rad\" -nt \"$THREADS\"
  else
    \"\$openradioss_root/exec/engine_linux64_gf\" -i \"${RUN_NAME}_0001.rad\" -nt \"$THREADS\"
  fi
'"

echo "Remote results: $HOST:$REMOTE_DIR"
