# Simple Injection Filling Pressure Distribution Report

Dataset: `data/datasets/Simple_Injection`

This model predicts Moldex3D filling pressure histogram summaries from geometry DOE and process DOE inputs.
Targets are `min/max/avg/sd` plus 10 volume-ratio bins from Moldex3D's histogram CSV export.

## Data

- Samples with filling pressure CSV: 120
- Geometry groups represented: 12
- Process combinations represented: 10
- Target columns: 14
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Ratio RMSE (%) | Ratio MAE (%) | Stats MAE (MPa) |
|---|---:|---:|---:|
| extra_trees | 2.1807 ± 0.6099 | 1.4338 ± 0.4380 | 1.4318 ± 0.6144 |
| hist_gradient_boosting | 2.2483 ± 0.4145 | 1.5838 ± 0.2457 | 1.4735 ± 0.5157 |
| random_forest | 2.2978 ± 0.6502 | 1.5673 ± 0.4759 | 1.9014 ± 0.8678 |
| ridge | 4.2415 ± 1.6002 | 2.6322 ± 0.7623 | 1.6359 ± 0.4428 |

## Caveat

This model predicts a histogram distribution, not a spatial contour field.
A true contour surrogate needs mesh-point or image/field exports with spatial coordinates.
