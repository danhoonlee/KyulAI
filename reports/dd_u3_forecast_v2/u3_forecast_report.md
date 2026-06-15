# DD u3 Forecast Training Report

- Dataset: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Input: theta1, theta2, and Case only. No force-displacement CSV or known Type is used at prediction time.
- Validation: GroupKFold by Test ID.

## Best Scalar Model
- `extra_trees`
- Pt MAE: 220.22 +/- 28.26 kips
- Pt R2: 0.894
- Max. Displacement MAE: 0.00571
- Max. Force MAE: 439.09
- Normalized curve RMSE: 0.0095
- u3 Type accuracy: 0.972
- u3 Type macro F1: 0.956

## GointMLP Forecast
- Pt MAE: 180.05 +/- 39.44 kips
- Pt R2: 0.913
- Max. Displacement MAE: 0.00263
- Max. Force MAE: 373.24
- Normalized curve RMSE: 0.0106

## Model Candidates
- `extra_trees`: Pt MAE 220.22, Pt R2 0.894
- `random_forest`: Pt MAE 270.53, Pt R2 0.871
