# Simple Injection Sprue Pressure Surrogate Report

Dataset: `data/datasets/Simple_Injection`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 30
- Geometry groups represented: 3
- Process combinations represented: 10
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| extra_trees | 3.6832 ± 0.6649 | 0.2040 ± 0.0318 | 0.1242 ± 0.0080 | 0.05587 ± 0.01211 |
| random_forest | 4.0677 ± 0.6749 | 1.0878 ± 0.0697 | 0.2988 ± 0.0192 | 0.05990 ± 0.01173 |
| ridge | 8.9084 ± 0.7063 | 0.6389 ± 0.0586 | 0.1405 ± 0.0199 | 0.13134 ± 0.01144 |
| neural_net_mlp_lbfgs | 11.0697 ± 5.2230 | 12.8618 ± 16.7101 | 1.2920 ± 1.5940 | 0.12424 ± 0.06366 |
| hist_gradient_boosting | 16.3156 ± 0.3613 | 12.5446 ± 0.1066 | 1.8592 ± 0.0183 | 0.22878 ± 0.00551 |

## Caveat

Only 30 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
