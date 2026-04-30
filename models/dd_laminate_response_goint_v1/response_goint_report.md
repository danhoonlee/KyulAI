# DD Response Goint Surrogate Report

This is a GointMLP-style multi-task neural surrogate from `theta1`, `theta2`, and case.
It predicts Type, Pt, max displacement, max force, and a normalized force-displacement curve.

- Samples: 400
- Sequence length: 128
- Validation: grouped 5-fold CV

| Metric | Mean | Std |
|---|---:|---:|
| Accuracy | 0.9350 | 0.0515 |
| Macro F1 | 0.9384 | 0.0458 |
| Pt MAE | 646.09 | 192.21 |
| Max displacement MAE | 0.000591 | 0.000601 |
| Max force MAE | 2542.01 | 786.18 |
| Curve normalized RMSE | 0.03892 | 0.00954 |
| Curve force RMSE | 2571.57 | 767.29 |

This model is useful as a deep-learning baseline, but the ExtraTrees+PCA surrogate remains the safer default on the current 400-sample dataset.
