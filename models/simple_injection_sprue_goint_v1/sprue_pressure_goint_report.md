# Simple Injection Goint Sprue Pressure Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.

- Samples: 300
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 5

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 2.7963 | 1.5995 |
| Max pressure MAE (MPa) | 0.7449 | 0.5847 |
| Max time MAE (s) | 0.1629 | 0.0872 |
| Normalized curve RMSE | 0.04035 | 0.02129 |

With 300 samples, this deep model is primarily a structural baseline; it should improve as the remaining DOE results arrive.
