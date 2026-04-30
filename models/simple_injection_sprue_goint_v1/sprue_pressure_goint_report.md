# Simple Injection Goint Sprue Pressure Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.

- Samples: 30
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 9.7977 | 1.2366 |
| Max pressure MAE (MPa) | 3.1498 | 1.4635 |
| Max time MAE (s) | 0.4624 | 0.2086 |
| Normalized curve RMSE | 0.14499 | 0.01992 |

With only 30 samples, this deep model is primarily a structural baseline; it should improve as the remaining 270 DOE results arrive.
