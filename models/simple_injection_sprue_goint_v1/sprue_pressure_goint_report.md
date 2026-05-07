# Simple Injection Goint Sprue Pressure Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.

- Samples: 150
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 5

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 3.5537 | 1.7720 |
| Max pressure MAE (MPa) | 1.3022 | 0.8380 |
| Max time MAE (s) | 0.2142 | 0.1297 |
| Normalized curve RMSE | 0.05140 | 0.02488 |

With 150 samples, this deep model is primarily a structural baseline; it should improve as the remaining DOE results arrive.
