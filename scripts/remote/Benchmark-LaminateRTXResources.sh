#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
DATA_DIR="${DATA_DIR:-data/datasets/DD_cases_2_3_4_geometry_v1}"
TEACHER_MODEL="${TEACHER_MODEL:-models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib}"
OUT_ROOT="${OUT_ROOT:-reports/rtx_resource_benchmarks/${RUN_ID}}"
CONFIGS="${CONFIGS:-0:auto,1:auto,2:auto,4:auto}"
BATCH_SIZE="${BATCH_SIZE:-512}"
EPOCHS="${EPOCHS:-2}"
SPLITS="${SPLITS:-2}"
TREE_N_JOBS="${TREE_N_JOBS:-8}"
PREFETCH_FACTOR="${PREFETCH_FACTOR:-2}"

mkdir -p "${OUT_ROOT}"
CSV="${OUT_ROOT}/resource_benchmark.csv"

echo "run_id,stage,num_workers,pin_memory,batch_size,epochs,splits,seconds,gpu_name,gpu_memory_used_mib,gpu_memory_total_mib" > "${CSV}"

echo "[run] ${RUN_ID}"
echo "[out] ${OUT_ROOT}"
echo "[configs] ${CONFIGS}"
echo "[batch_size] ${BATCH_SIZE}"
echo "[epochs] ${EPOCHS}"
echo "[splits] ${SPLITS}"
echo "[tree_n_jobs] ${TREE_N_JOBS}"
echo "[repo] $(pwd)"
echo "[commit] $(git rev-parse --short HEAD)"

python - <<'PY'
import torch
print("[torch]", torch.__version__)
print("[cuda_available]", torch.cuda.is_available())
print("[cuda_device]", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY

if [ ! -d "${DATA_DIR}" ]; then
  python scripts/dd_build_geometry_response_dataset.py --output-root "${DATA_DIR}"
fi

nvidia_query() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits | head -1
  elif [ -x /usr/lib/wsl/lib/nvidia-smi ]; then
    /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits | head -1
  else
    echo "unknown,0,0"
  fi
}

run_case() {
  local stage="$1"
  local workers="$2"
  local pin_memory="$3"
  local out_dir="${OUT_ROOT}/${stage}_workers${workers}_pin${pin_memory}"
  local start
  local elapsed
  local gpu_line

  rm -rf "${out_dir}"
  echo "[case] stage=${stage} workers=${workers} pin_memory=${pin_memory}"
  start="${SECONDS}"

  if [ "${stage}" = "distill-final" ]; then
    python scripts/dd_response_distillation_train.py \
      --data-dir "${DATA_DIR}" \
      --teacher-model "${TEACHER_MODEL}" \
      --output-dir "${out_dir}" \
      --model-name "benchmark_${RUN_ID}_${stage}_w${workers}_pin${pin_memory}" \
      --feature-set theta_physics_geometry_v1 \
      --device cuda \
      --final-only \
      --final-epochs "${EPOCHS}" \
      --batch-size "${BATCH_SIZE}" \
      --num-workers "${workers}" \
      --pin-memory "${pin_memory}" \
      --prefetch-factor "${PREFETCH_FACTOR}" \
      --synthetic-grid-step 0 >/dev/null
  elif [ "${stage}" = "goint-cv" ]; then
    python scripts/dd_response_physics_xai_train.py \
      --data-dir "${DATA_DIR}" \
      --tree-output-dir "${out_dir}/tree" \
      --goint-output-dir "${out_dir}/goint" \
      --report "${out_dir}/report.md" \
      --feature-set theta_physics_geometry_v1 \
      --device cuda \
      --skip-tree \
      --splits "${SPLITS}" \
      --epochs "${EPOCHS}" \
      --final-epochs "${EPOCHS}" \
      --batch-size "${BATCH_SIZE}" \
      --num-workers "${workers}" \
      --pin-memory "${pin_memory}" \
      --prefetch-factor "${PREFETCH_FACTOR}" \
      --tree-n-jobs "${TREE_N_JOBS}" >/dev/null
  else
    echo "Unknown stage: ${stage}" >&2
    exit 2
  fi

  elapsed=$((SECONDS - start))
  gpu_line="$(nvidia_query)"
  echo "${RUN_ID},${stage},${workers},${pin_memory},${BATCH_SIZE},${EPOCHS},${SPLITS},${elapsed},${gpu_line}" >> "${CSV}"
  echo "[done] stage=${stage} workers=${workers} pin_memory=${pin_memory} seconds=${elapsed}"
}

IFS=',' read -ra CONFIG_ITEMS <<< "${CONFIGS}"
for item in "${CONFIG_ITEMS[@]}"; do
  workers="${item%%:*}"
  pin_memory="${item#*:}"
  run_case "distill-final" "${workers}" "${pin_memory}"
  run_case "goint-cv" "${workers}" "${pin_memory}"
done

echo "[csv] ${CSV}"
cat "${CSV}"
