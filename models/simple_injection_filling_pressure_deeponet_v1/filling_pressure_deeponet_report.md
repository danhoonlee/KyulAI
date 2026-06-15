# Simple Injection Filling Pressure DeepONet Report

This is a DeepONet-style branch/trunk surrogate for filling pressure histogram summaries.

- Samples: 360
- Input dimension: 23
- Output dimension: 14
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Volume ratio RMSE (%) | 2.0706 | 0.3797 |
| Volume ratio MAE (%) | 1.1817 | 0.1787 |
| Stats MAE (MPa) | 0.8073 | 0.2107 |

Weak physics-informed penalties are enabled for nonnegative values, histogram ratio sum = 100%, and min/avg/max consistency.
