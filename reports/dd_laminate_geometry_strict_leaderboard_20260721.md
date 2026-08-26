# DD Laminate Geometry-Aware Strict Leaderboard - 2026-07-21

This report summarizes the RTX WSL strict grouped-CV run for the geometry-aware Laminate Forecast models.

## Run

- Run id: `20260721_geometry_strict_rtx_v2`
- Remote commit: `d789947`
- Device: `NVIDIA GeForce RTX 5070`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Cases: Case 2, Case 3, Case 4
- Panel sizes: `6x4`, `6x8`
- Feature set: `theta_physics_geometry_v1`
- Validation: 5-fold strict grouped CV

## Dataset Composition

| Case | Rows | 6x4 curated | 6x8 new data |
| --- | ---: | ---: | ---: |
| Case 2 | 600 | 300 | 300 |
| Case 3 | 600 | 300 | 300 |
| Case 4 | 600 | 300 | 300 |
| Total | 1800 | 900 | 900 |

## Model Leaderboard

| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Geometry Tree + Physics XAI | 0.9561 +/- 0.0106 | 0.9511 +/- 0.0149 | 313.91 +/- 50.55 | 0.00571 +/- 0.00086 | 401.38 +/- 66.36 | Best all-around deployment candidate; strongest Pt and curve regression. |
| Geometry Hybrid Student | 0.9622 +/- 0.0117 | 0.9601 +/- 0.0143 | 423.02 +/- 47.02 | 0.00951 +/- 0.00094 | 648.20 +/- 29.84 | Best Type classification; distilled from Tree teacher plus synthetic theta/case/panel grid. |
| Geometry GointMLP + Physics XAI | 0.9511 +/- 0.0080 | 0.9480 +/- 0.0108 | 738.04 +/- 116.19 | 0.02698 +/- 0.01042 | 1241.92 +/- 341.99 | Useful deep-learning baseline, but not ready to replace Tree/Hybrid for Pt or curve. |

## Fixed Holdout Gate

The same models were also evaluated with a deterministic 20% fixed holdout split. The holdout uses `Case + theta1 + theta2` as the group key, so no identical case/theta pair appears in both train and holdout.

- Holdout run id: `20260721_geometry_holdout_rtx_v1`
- Train rows: 1436
- Holdout rows: 364
- Train groups: 718
- Holdout groups: 182
- Holdout panel sizes: 182 rows from `6x4` and 182 rows from `6x8`

| Model | Holdout Type Acc. | Holdout Macro F1 | Holdout Pt MAE (kips) | Holdout Curve Norm RMSE | Holdout Curve Force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree + Physics XAI | 0.9451 | 0.9456 | 247.39 | 0.00293 | 227.99 |
| Geometry Hybrid Student | 0.9451 | 0.9444 | 361.05 | 0.00576 | 425.69 |
| Geometry GointMLP + Physics XAI | 0.9203 | 0.9247 | 675.61 | 0.01838 | 1035.00 |

## Hybrid Distillation Details

- Teacher: `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`
- Synthetic grid step: `2.5` degrees
- Synthetic panel sizes: `6x4,6x8`
- Synthetic samples: 31974
- Synthetic base weight: 0.28
- Synthetic confidence power: 1.5
- Strict synthetic exclusion radius: 2.5 degrees
- Teacher Type agreement: 0.9789
- Pt MAE vs teacher: 333.96 kips
- Curve normalized RMSE vs teacher: 0.00755

## Interpretation

The Geometry Tree model remains the safest deployment default because it has the lowest Pt MAE and curve error. The Hybrid Student is now the strongest Type classifier and is useful as a compact or Type-focused challenger, but it does not yet beat the Tree model on the response quantities users inspect most directly.

The fixed holdout gate strengthens the same decision: Tree and Hybrid tie on Type accuracy, but Tree has substantially better Pt and curve errors on the non-moving holdout set.

For product behavior, keep `Laminate Forecast - Machine Learning` mapped to the Geometry Tree model unless the user explicitly selects or requests the distilled student. For research, continue tracking Hybrid Student because it is the most promising route for fast inference and smoother design-space behavior.

## Source Reports

- `reports/dd_response_geometry_rtx_strict_20260721_geometry_strict_rtx_v2/response_geometry_training_report.md`
- `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v2/distillation_report.md`
- `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v2/response_distilled_metrics.json`
- `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_report.md`
- `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_metrics.json`
- `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_manifest.csv`
