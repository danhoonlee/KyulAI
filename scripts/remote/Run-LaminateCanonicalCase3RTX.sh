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
TREE_N_JOBS="${TREE_N_JOBS:-8}"
NUM_WORKERS="${NUM_WORKERS:-2}"
PIN_MEMORY="${PIN_MEMORY:-auto}"
PREFETCH_FACTOR="${PREFETCH_FACTOR:-2}"
RUN_HOLDOUT="${RUN_HOLDOUT:-1}"
RUN_XAI="${RUN_XAI:-1}"
RUN_U3="${RUN_U3:-1}"

FEATURE_SET="theta_physics_geometry_canonical_v2"
U3_FEATURE_SET="theta_physics_compact_canonical_v2"
DATA_DIR="data/datasets/DD_cases_2_3_4_geometry_v1"
U3_MANIFEST="data/datasets/DD_u3_pt_v2/manifest.csv"

TREE_DIR="models/dd_laminate_response_geometry_tree_canonical_v2"
GOINT_DIR="models/dd_laminate_response_geometry_goint_canonical_v2"
HYBRID_DIR="models/dd_laminate_response_hybrid_student_canonical_v2"
TRAIN_REPORT_DIR="reports/dd_response_geometry_canonical_v2"
HYBRID_CV_DIR="reports/dd_response_hybrid_canonical_v2_strict_cv"
HOLDOUT_DIR="reports/dd_response_geometry_canonical_v2_fixed_holdout"
TREE_XAI_DIR="reports/dd_response_xai_geometry_tree_canonical_v2"
GOINT_XAI_DIR="reports/dd_response_xai_geometry_goint_canonical_v2"
HYBRID_XAI_DIR="reports/dd_response_xai_hybrid_student_canonical_v2"
U3_MODEL_DIR="models/dd_laminate_u3_forecast_physics_canonical_v2"
U3_REPORT_DIR="reports/dd_u3_forecast_physics_canonical_v2"

echo "[run] ${RUN_ID}"
echo "[device] ${DEVICE}"
echo "[feature_set] ${FEATURE_SET}"
echo "[panel_sizes] ${PANEL_SIZES}"
echo "[repo] $(pwd)"
echo "[commit] $(git rev-parse --short HEAD)"

python - <<'PY'
import torch

print("[torch]", torch.__version__)
print("[cuda_available]", torch.cuda.is_available())
print("[cuda_device]", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY

python -m py_compile \
  src/ml/dd_laminate/case_definitions.py \
  src/ml/dd_laminate/laminate_physics.py \
  src/ml/dd_laminate/response_feature_sets.py \
  src/ml/dd_laminate/train_u3_forecast_models.py \
  scripts/dd_response_physics_xai_train.py \
  scripts/dd_response_distillation_train.py \
  scripts/dd_response_geometry_holdout_eval.py \
  scripts/dd_response_xai_report.py

python -m pytest -q tests/unit/ml/test_dd_case_definitions.py

python scripts/dd_build_geometry_response_dataset.py \
  --output-root "${DATA_DIR}"

echo "[stage] Canonical Case3 Geometry Tree and GointMLP"
python scripts/dd_response_physics_xai_train.py \
  --data-dir "${DATA_DIR}" \
  --tree-output-dir "${TREE_DIR}" \
  --goint-output-dir "${GOINT_DIR}" \
  --report "${TRAIN_REPORT_DIR}/response_geometry_training_report.md" \
  --feature-set "${FEATURE_SET}" \
  --device "${DEVICE}" \
  --splits 5 \
  --epochs "${EPOCHS}" \
  --final-epochs "${FINAL_EPOCHS}" \
  --patience 36 \
  --batch-size "${BATCH_SIZE}" \
  --tree-n-jobs "${TREE_N_JOBS}" \
  --num-workers "${NUM_WORKERS}" \
  --pin-memory "${PIN_MEMORY}" \
  --prefetch-factor "${PREFETCH_FACTOR}" \
  --response-hidden-dim 96 \
  --response-branches 10 \
  --dropout 0.08 \
  --lr 6e-4 \
  --weight-decay 7e-4

echo "[stage] Canonical Case3 Hybrid Student strict grouped CV"
python scripts/dd_response_distillation_train.py \
  --data-dir "${DATA_DIR}" \
  --teacher-model "${TREE_DIR}/response_surrogate.joblib" \
  --output-dir "${HYBRID_CV_DIR}" \
  --model-name laminate_forecast_hybrid_canonical_v2_strict_cv \
  --feature-set "${FEATURE_SET}" \
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
  --tree-n-jobs "${TREE_N_JOBS}" \
  --num-workers "${NUM_WORKERS}" \
  --pin-memory "${PIN_MEMORY}" \
  --prefetch-factor "${PREFETCH_FACTOR}" \
  --hidden-dim 96 \
  --branches 10 \
  --dropout 0.08 \
  --lr 6e-4 \
  --weight-decay 7e-4

echo "[stage] Canonical Case3 Hybrid Student final deployment artifact"
python scripts/dd_response_distillation_train.py \
  --data-dir "${DATA_DIR}" \
  --teacher-model "${TREE_DIR}/response_surrogate.joblib" \
  --output-dir "${HYBRID_DIR}" \
  --model-name laminate_forecast_hybrid_canonical_v2 \
  --feature-set "${FEATURE_SET}" \
  --device "${DEVICE}" \
  --final-only \
  --reference-metrics "${HYBRID_CV_DIR}/response_distilled_metrics.json" \
  --synthetic-grid-step "${GRID_STEP}" \
  --synthetic-panel-sizes "${PANEL_SIZES}" \
  --synthetic-weight "${SYNTHETIC_WEIGHT}" \
  --synthetic-confidence-power "${CONFIDENCE_POWER}" \
  --synthetic-min-confidence-weight 0.45 \
  --final-epochs "${FINAL_EPOCHS}" \
  --batch-size "${BATCH_SIZE}" \
  --num-workers "${NUM_WORKERS}" \
  --pin-memory "${PIN_MEMORY}" \
  --prefetch-factor "${PREFETCH_FACTOR}" \
  --hidden-dim 96 \
  --branches 10 \
  --dropout 0.08 \
  --lr 6e-4 \
  --weight-decay 7e-4

if [[ "${RUN_HOLDOUT}" == "1" ]]; then
  echo "[stage] Canonical Case3 fixed grouped holdout"
  python scripts/dd_response_geometry_holdout_eval.py \
    --data-dir "${DATA_DIR}" \
    --output-dir "${HOLDOUT_DIR}" \
    --feature-set "${FEATURE_SET}" \
    --device "${DEVICE}" \
    --epochs "${EPOCHS}" \
    --patience 36 \
    --batch-size "${BATCH_SIZE}" \
    --tree-n-jobs "${TREE_N_JOBS}" \
    --num-workers "${NUM_WORKERS}" \
    --pin-memory "${PIN_MEMORY}" \
    --prefetch-factor "${PREFETCH_FACTOR}" \
    --response-hidden-dim 96 \
    --response-branches 10 \
    --hidden-dim 96 \
    --branches 10 \
    --dropout 0.08 \
    --lr 6e-4 \
    --weight-decay 7e-4 \
    --synthetic-grid-step "${GRID_STEP}" \
    --synthetic-panel-sizes "${PANEL_SIZES}" \
    --synthetic-weight "${SYNTHETIC_WEIGHT}" \
    --synthetic-confidence-power "${CONFIDENCE_POWER}"
fi

if [[ "${RUN_XAI}" == "1" ]]; then
  echo "[stage] Canonical Case3 XAI artifacts"
  python scripts/dd_response_xai_report.py \
    --model "${TREE_DIR}/response_surrogate.joblib" \
    --data-dir "${DATA_DIR}" \
    --output-dir "${TREE_XAI_DIR}" \
    --model-kind tree \
    --device "${DEVICE}"
  python scripts/dd_response_xai_report.py \
    --model "${GOINT_DIR}/response_goint.pt" \
    --data-dir "${DATA_DIR}" \
    --output-dir "${GOINT_XAI_DIR}" \
    --model-kind goint \
    --device "${DEVICE}"
  python scripts/dd_response_xai_report.py \
    --model "${HYBRID_DIR}/response_goint.pt" \
    --data-dir "${DATA_DIR}" \
    --output-dir "${HYBRID_XAI_DIR}" \
    --model-kind goint \
    --device "${DEVICE}"
fi

if [[ "${RUN_U3}" == "1" ]]; then
  echo "[stage] Canonical Case3 u3 Tree and GointMLP"
  python -m src.ml.dd_laminate.train_u3_forecast_models \
    --manifest "${U3_MANIFEST}" \
    --output-dir "${U3_MODEL_DIR}" \
    --report-dir "${U3_REPORT_DIR}" \
    --feature-set "${U3_FEATURE_SET}" \
    --splits 5
fi

echo "[done] ${RUN_ID}"
echo "[tree] ${TREE_DIR}"
echo "[goint] ${GOINT_DIR}"
echo "[hybrid] ${HYBRID_DIR}"
echo "[holdout] ${HOLDOUT_DIR}"
echo "[u3] ${U3_MODEL_DIR}"
