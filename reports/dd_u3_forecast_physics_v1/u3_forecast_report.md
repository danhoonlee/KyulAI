# DD u3 Forecast Training Report

- Dataset: `/Users/danlee/KyulAI_codex/data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Input: theta1, theta2, and Case only. No force-displacement CSV or known Type is used at prediction time.
- Feature set: `theta_physics`
- Validation: GroupKFold by Test ID.

## Best Scalar Model
- `extra_trees`
- Pt MAE: 218.29 +/- 5.08 kips
- Pt R2: 0.913
- Max. Displacement MAE: 0.00438
- Max. Force MAE: 288.07
- Normalized curve RMSE: 0.0070
- u3 Type accuracy: 0.974
- u3 Type macro F1: 0.960

## GointMLP Forecast
- Pt MAE: 163.35 +/- 28.59 kips
- Pt R2: 0.926
- Max. Displacement MAE: 0.00262
- Max. Force MAE: 361.35
- Normalized curve RMSE: 0.0104

## Model Candidates
- `extra_trees`: Pt MAE 218.29, Pt R2 0.913
- `random_forest`: Pt MAE 237.29, Pt R2 0.898
