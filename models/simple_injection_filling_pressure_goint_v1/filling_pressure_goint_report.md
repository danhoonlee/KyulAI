# Simple Injection Filling Pressure Goint Report

This is a GointMLP-style multi-branch neural surrogate for Moldex3D filling pressure histogram summaries.

- Samples: 120
- Input dimension: 23
- Output dimension: 14
- Validation mode: `grouped`; folds: 3

| Metric | Mean | Std |
|---|---:|---:|
| Volume ratio RMSE (%) | 2.3034 | 0.5097 |
| Volume ratio MAE (%) | 1.5814 | 0.3273 |
| Stats MAE (MPa) | 2.3191 | 0.6258 |
