#!/usr/bin/env bash
# Retrain the served 3-size response family on kink Pt, development rows only.
#
# Recipe is Run-LaminateGeometryStrictRTX.sh with three changes: kink-Pt data, the canonical
# feature builder, and all three panels. Base models see only the development partition, so
# the pt_consistent models warm-started from them never see a holdout row, and the holdout in
# reports/dd_response_geometry_split_v2_3size measures exactly what is served.
#
# SKIP_BASE=1 reuses existing base models.
# Prerequisite: python scripts/dd_build_kink_pt_dataset.py curated / geometry.
set -euo pipefail

PY="${PY:-.venv/bin/python}"
DEVICE="${DEVICE:-cuda}"
FS="theta_physics_geometry_canonical_v2"
DEV="data/datasets/DD_cases_2_3_4_geometry_3size_kink_dev_v1"
FULL="data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1"
SPLIT="${FULL}/split_manifest.csv"
BASE_TREE="models/dd_laminate_response_geometry_tree_3size_kink_dev_v1"
BASE_GOINT="models/dd_laminate_response_geometry_goint_3size_kink_dev_v1"
BASE_HYBRID="models/dd_laminate_response_hybrid_student_3size_kink_dev_v1"
PT_TREE="models/dd_laminate_response_pt_consistent_tree_3size_kink_v1"
PT_GOINT="models/dd_laminate_response_pt_consistent_goint_3size_kink_v1"
PT_HYBRID="models/dd_laminate_response_pt_consistent_hybrid_3size_kink_v1"
REPORTS="reports/dd_response_3size_kink_v1"

echo "[commit] $(git rev-parse --short HEAD)"
if [[ "${SKIP_BASE:-0}" != "1" ]]; then
echo "[stage] base tree + GointMLP (development rows only)"
"${PY}" scripts/dd_response_physics_xai_train.py \
  --data-dir "${DEV}" \
  --tree-output-dir "${BASE_TREE}" \
  --goint-output-dir "${BASE_GOINT}" \
  --report "${REPORTS}/base_tree_goint_training_report.md" \
  --feature-set "${FS}" \
  --device "${DEVICE}" \
  --splits 5 --epochs 220 --final-epochs 170 --patience 36 --batch-size 512 \
  --tree-n-jobs 8 --num-workers 2 --pin-memory auto --prefetch-factor 2 \
  --response-hidden-dim 96 --response-branches 10 --dropout 0.08 --lr 6e-4 --weight-decay 7e-4

echo "[stage] base Hybrid Student (development rows only)"
"${PY}" scripts/dd_response_distillation_train.py \
  --data-dir "${DEV}" \
  --teacher-model "${BASE_TREE}/response_surrogate.joblib" \
  --output-dir "${BASE_HYBRID}" \
  --model-name laminate_forecast_hybrid_3size_kink_dev_v1 \
  --feature-set "${FS}" \
  --device "${DEVICE}" \
  --final-only \
  --synthetic-grid-step 2.5 --synthetic-panel-sizes 6x4,6x8,8x8 \
  --synthetic-weight 0.28 --synthetic-confidence-power 1.5 --synthetic-min-confidence-weight 0.45 \
  --teacher-n-components 18 --epochs 220 --final-epochs 170 --patience 36 --batch-size 512 \
  --tree-n-jobs 8 --num-workers 2 --pin-memory auto --prefetch-factor 2 \
  --hidden-dim 96 --branches 10 --dropout 0.08 --lr 6e-4 --weight-decay 7e-4
fi

echo "[stage] pt_consistent tree"
"${PY}" scripts/dd_response_pt_consistent_tree_train.py \
  --data-dir "${FULL}" --split-manifest "${SPLIT}" \
  --baseline-model "${BASE_TREE}/response_surrogate.joblib" \
  --output-dir "${PT_TREE}" --report-dir "${REPORTS}/pt_consistent_tree" \
  --feature-set "${FS}"

echo "[stage] pt_consistent GointMLP + Hybrid"
"${PY}" scripts/dd_response_pt_consistent_deep_train.py \
  --data-dir "${FULL}" --split-manifest "${SPLIT}" \
  --goint-baseline "${BASE_GOINT}/response_goint.pt" \
  --hybrid-baseline "${BASE_HYBRID}/response_goint.pt" \
  --teacher-model "${PT_TREE}/response_surrogate.joblib" \
  --goint-output-dir "${PT_GOINT}" --hybrid-output-dir "${PT_HYBRID}" \
  --report-dir "${REPORTS}/pt_consistent_deep" \
  --feature-set "${FS}" --device "${DEVICE}"

echo "[done]"
