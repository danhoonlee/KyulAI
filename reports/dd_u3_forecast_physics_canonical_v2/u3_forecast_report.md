# DD u3 Forecast Training Report

- Dataset: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Input: theta1, theta2, and Case only. No force-displacement CSV or known Type is used at prediction time.
- Feature set: `theta_physics_compact_canonical_v2`
- Validation: GroupKFold by Test ID.

## Best Scalar Model
- `extra_trees`
- Pt MAE: 227.88 +/- 19.24 kips
- Pt R2: 0.914
- Max. Displacement MAE: 0.00361
- Max. Force MAE: 230.57
- Normalized curve RMSE: 0.0064
- u3 Type accuracy: 0.979
- u3 Type macro F1: 0.967

## GointMLP Forecast
- Pt MAE: 166.16 +/- 36.02 kips
- Pt R2: 0.923
- Max. Displacement MAE: 0.00249
- Max. Force MAE: 341.95
- Normalized curve RMSE: 0.0102

## Model Candidates
- `extra_trees`: Pt MAE 227.88, Pt R2 0.914
- `random_forest`: Pt MAE 241.72, Pt R2 0.900
