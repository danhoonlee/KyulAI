# DD Response Goint Surrogate Report

This is a GointMLP-style multi-task neural surrogate from `theta1`, `theta2`, and case.
It predicts Type, Pt, max displacement, max force, and a normalized force-displacement curve.

- Samples: 500
- Sequence length: 128
- Validation: grouped 5-fold CV

| Metric | Mean | Std |
|---|---:|---:|
| Accuracy | 0.9460 | 0.0265 |
| Macro F1 | 0.9472 | 0.0329 |
| Pt MAE | 533.09 | 146.10 |
| Max displacement MAE | 0.000466 | 0.000279 |
| Max force MAE | 1634.25 | 157.76 |
| Curve normalized RMSE | 0.03155 | 0.00717 |
| Curve force RMSE | 1653.11 | 226.87 |

This model is useful as a deep-learning baseline, but the ExtraTrees+PCA surrogate remains the safer default on the current 400-sample dataset.
