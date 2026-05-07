# Simple Injection Sprue Pressure Surrogate Report

Dataset: `data/datasets/Simple_Injection`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 150
- Geometry groups represented: 15
- Process combinations represented: 10
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| extra_trees | 2.0163 ± 0.2101 | 0.1023 ± 0.0271 | 0.0963 ± 0.0059 | 0.03064 ± 0.00207 |
| hist_gradient_boosting | 2.0277 ± 0.3364 | 0.2059 ± 0.0392 | 0.0940 ± 0.0048 | 0.03068 ± 0.00403 |
| random_forest | 2.0362 ± 0.2983 | 0.1066 ± 0.0466 | 0.0960 ± 0.0045 | 0.03080 ± 0.00368 |
| ridge | 7.7862 ± 0.5394 | 0.6404 ± 0.2167 | 0.1352 ± 0.0399 | 0.11380 ± 0.00784 |
| neural_net_mlp_lbfgs | 19.2177 ± 32.4173 | 5.8155 ± 8.5862 | 0.5135 ± 0.6511 | 0.15091 ± 0.21561 |

## Caveat

Only 150 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
