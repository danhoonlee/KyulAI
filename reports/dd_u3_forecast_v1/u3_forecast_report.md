# DD u3 Forecast Training Report

- Dataset: `/Users/danlee/KyulAI_codex/data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Input: theta1, theta2, Case, and u3 bucket only. No force-displacement CSV is used at prediction time.
- Validation: GroupKFold by Test ID.

## Best Scalar Model
- `extra_trees`
- Pt MAE: 219.31 +/- 28.80 kips
- Pt R2: 0.896
- Max. Displacement MAE: 0.00568
- Max. Force MAE: 437.24
- Normalized curve RMSE: 0.0094

## GointMLP Forecast
- Pt MAE: 181.74 +/- 48.54 kips
- Pt R2: 0.918
- Max. Displacement MAE: 0.00257
- Max. Force MAE: 378.87
- Normalized curve RMSE: 0.0101

## Model Candidates
- `extra_trees`: Pt MAE 219.31, Pt R2 0.896
- `random_forest`: Pt MAE 270.75, Pt R2 0.871
