# Simple Injection DeepONet Sprue Pressure Report

This is a DeepONet-style operator surrogate for Moldex3D sprue pressure.
The branch network encodes DOE features, and the trunk network encodes normalized time.

- Samples: 360
- Input dimension: 23
- Sequence length: 128
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Pressure curve RMSE (MPa) | 5.4207 | 0.7754 |
| Max pressure MAE (MPa) | 0.9010 | 0.5603 |
| Max time MAE (s) | 0.1536 | 0.0456 |
| Normalized curve RMSE | 0.07831 | 0.00871 |
| Shape correlation | 0.9786 | 0.0038 |
| Normalized AUC MAE | 0.00859 | 0.00174 |
| Pressure-time AUC MAE (MPa*s) | 13.5577 | 3.6965 |
| Peak position MAE (normalized time) | 0.04705 | 0.01158 |
| Rise slope MAE (normalized) | 9.0905 | 3.1844 |

Weak physics-informed penalties are enabled for nonnegative pressure, peak timing, and oscillation suppression.

This model is intended for shape-aware curve behavior on user-edited DOE combinations.
