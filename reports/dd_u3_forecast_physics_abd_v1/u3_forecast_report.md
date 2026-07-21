# DD u3 Forecast Training Report

- Dataset: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Input: theta1, theta2, and Case only. No force-displacement CSV or known Type is used at prediction time.
- Feature set: `theta_physics_v2`
- Validation: GroupKFold by Test ID.

## Best Scalar Model
- `extra_trees`
- Pt MAE: 223.78 +/- 8.83 kips
- Pt R2: 0.913
- Max. Displacement MAE: 0.00443
- Max. Force MAE: 289.32
- Normalized curve RMSE: 0.0070
- u3 Type accuracy: 0.975
- u3 Type macro F1: 0.962

## GointMLP Forecast
- Pt MAE: 168.65 +/- 36.49 kips
- Pt R2: 0.923
- Max. Displacement MAE: 0.00233
- Max. Force MAE: 337.72
- Normalized curve RMSE: 0.0102

## Model Candidates
- `extra_trees`: Pt MAE 223.78, Pt R2 0.913
- `random_forest`: Pt MAE 244.21, Pt R2 0.897
