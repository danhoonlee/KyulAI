#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
DEVICE="${DEVICE:-cuda}"
GRID_STEP="${GRID_STEP:-2.5}"
SYNTHETIC_WEIGHT="${SYNTHETIC_WEIGHT:-0.28}"
CONFIDENCE_POWER="${CONFIDENCE_POWER:-1.5}"
EPOCHS="${EPOCHS:-220}"
FINAL_EPOCHS="${FINAL_EPOCHS:-170}"
BATCH_SIZE="${BATCH_SIZE:-512}"
PANEL_SIZES="${PANEL_SIZES:-6x4,6x8}"

GEOMETRY_TREE_DIR="models/dd_laminate_response_geometry_tree_rtx_strict_${RUN_ID}"
GEOMETRY_GOINT_DIR="models/dd_laminate_response_geometry_goint_rtx_strict_${RUN_ID}"
GEOMETRY_REPORT="reports/dd_response_geometry_rtx_strict_${RUN_ID}/response_geometry_training_report.md"
HYBRID_DIR="reports/dd_response_hybrid_geometry_strict_cv_${RUN_ID}"

echo "[run] ${RUN_ID}"
echo "[device] ${DEVICE}"
echo "[panel_sizes] ${PANEL_SIZES}"
echo "[grid_step] ${GRID_STEP}"
echo "[repo] $(pwd)"
echo "[commit] $(git rev-parse --short HEAD)"

python - <<'PY'
import torch
print("[torch]", torch.__version__)
print("[cuda_available]", torch.cuda.is_available())
print("[cuda_device]", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY

python -m py_compile scripts/dd_response_physics_xai_train.py scripts/dd_response_distillation_train.py

python scripts/dd_build_geometry_response_dataset.py \
  --output-root data/datasets/DD_cases_2_3_4_geometry_v1

echo "[stage] Geometry ML/DL strict grouped CV"
python scripts/dd_response_physics_xai_train.py \
  --data-dir data/datasets/DD_cases_2_3_4_geometry_v1 \
  --tree-output-dir "${GEOMETRY_TREE_DIR}" \
  --goint-output-dir "${GEOMETRY_GOINT_DIR}" \
  --report "${GEOMETRY_REPORT}" \
  --feature-set theta_physics_geometry_v1 \
  --device "${DEVICE}" \
  --splits 5 \
  --epochs "${EPOCHS}" \
  --final-epochs "${FINAL_EPOCHS}" \
  --patience 36 \
  --batch-size "${BATCH_SIZE}" \
  --response-hidden-dim 96 \
  --response-branches 10 \
  --dropout 0.08 \
  --lr 6e-4 \
  --weight-decay 7e-4

echo "[stage] Geometry-aware Hybrid Student strict CV"
python scripts/dd_response_distillation_train.py \
  --data-dir data/datasets/DD_cases_2_3_4_geometry_v1 \
  --teacher-model models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib \
  --output-dir "${HYBRID_DIR}" \
  --model-name laminate_forecast_hybrid_geometry_strict_cv_${RUN_ID} \
  --feature-set theta_physics_geometry_v1 \
  --device "${DEVICE}" \
  --strict-cv \
  --strict-cv-only \
  --strict-synthetic-exclusion-radius "${GRID_STEP}" \
  --synthetic-grid-step "${GRID_STEP}" \
  --synthetic-panel-sizes "${PANEL_SIZES}" \
  --synthetic-weight "${SYNTHETIC_WEIGHT}" \
  --synthetic-confidence-power "${CONFIDENCE_POWER}" \
  --synthetic-min-confidence-weight 0.45 \
  --teacher-n-components 18 \
  --epochs "${EPOCHS}" \
  --patience 36 \
  --batch-size "${BATCH_SIZE}" \
  --hidden-dim 96 \
  --branches 10 \
  --dropout 0.08 \
  --lr 6e-4 \
  --weight-decay 7e-4

echo "[done] ${RUN_ID}"
echo "[geometry_report] ${GEOMETRY_REPORT}"
echo "[hybrid_report] ${HYBRID_DIR}/distillation_report.md"
