# Simple Injection Goint Sprue Pressure Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.

- Samples: 360
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 2.9166 | 1.0316 |
| Max pressure MAE (MPa) | 0.7137 | 0.3371 |
| Max time MAE (s) | 0.1545 | 0.0324 |
| Normalized curve RMSE | 0.04040 | 0.01230 |
| Shape correlation | 0.9941 | 0.0042 |
| Normalized AUC MAE | 0.00652 | 0.00172 |
| Pressure-time AUC MAE (MPa*s) | 9.9165 | 3.9940 |
| Peak position MAE (normalized time) | 0.08672 | 0.00395 |
| Rise slope MAE (normalized) | 5.8876 | 0.9967 |

Weak physics-informed penalties are enabled for nonnegative pressure, peak timing, and oscillation suppression.

With 360 samples, this deep model is primarily a structural baseline; it should improve as the remaining DOE results arrive.
