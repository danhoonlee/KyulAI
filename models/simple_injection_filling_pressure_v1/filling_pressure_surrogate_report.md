# Simple Injection Filling Pressure Distribution Report

Dataset: `data/datasets/Simple_Injection`

This model predicts Moldex3D filling pressure histogram summaries from geometry DOE and process DOE inputs.
Targets are `min/max/avg/sd` plus 10 volume-ratio bins from Moldex3D's histogram CSV export.

## Data

- Samples with filling pressure CSV: 360
- Geometry groups represented: 42
- Process combinations represented: 20
- Target columns: 14
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Ratio RMSE (%) | Ratio MAE (%) | Stats MAE (MPa) |
|---|---:|---:|---:|
| extra_trees | 2.0705 ± 0.3000 | 1.2595 ± 0.1930 | 0.7570 ± 0.1299 |
| random_forest | 2.1581 ± 0.5569 | 1.3487 ± 0.3662 | 1.0869 ± 0.2021 |
| hist_gradient_boosting | 2.3008 ± 0.6385 | 1.4042 ± 0.3634 | 0.8676 ± 0.0711 |
| ridge | 2.8819 ± 0.4263 | 1.7820 ± 0.1861 | 1.0536 ± 0.2602 |

## Caveat

This model predicts a histogram distribution, not a spatial contour field.
A true contour surrogate needs mesh-point or image/field exports with spatial coordinates.
