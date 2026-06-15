# Simple Injection Filling Pressure Goint Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D filling pressure histogram summaries.

- Samples: 360
- Input dimension: 23
- Output dimension: 14
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Volume ratio RMSE (%) | 2.1473 | 0.2189 |
| Volume ratio MAE (%) | 1.1733 | 0.1269 |
| Stats MAE (MPa) | 1.1115 | 0.2462 |

Weak physics-informed penalties are enabled for nonnegative values, histogram ratio sum = 100%, and min/avg/max consistency.
