# Simple Injection Goint Sprue Pressure Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.

- Samples: 240
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 5

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 2.7652 | 1.1336 |
| Max pressure MAE (MPa) | 0.8706 | 0.6439 |
| Max time MAE (s) | 0.1673 | 0.0682 |
| Normalized curve RMSE | 0.03984 | 0.01412 |

With 240 samples, this deep model is primarily a structural baseline; it should improve as the remaining DOE results arrive.
