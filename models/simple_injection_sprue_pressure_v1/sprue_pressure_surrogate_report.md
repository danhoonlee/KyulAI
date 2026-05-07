# Simple Injection Sprue Pressure Surrogate Report

Dataset: `data/datasets/Simple_Injection`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 300
- Geometry groups represented: 30
- Process combinations represented: 10
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `hist_gradient_boosting`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| hist_gradient_boosting | 1.8719 ± 0.1140 | 0.1048 ± 0.0376 | 0.0955 ± 0.0034 | 0.02843 ± 0.00206 |
| extra_trees | 1.9107 ± 0.1015 | 0.0539 ± 0.0222 | 0.0960 ± 0.0033 | 0.02914 ± 0.00185 |
| random_forest | 1.9157 ± 0.1005 | 0.0558 ± 0.0330 | 0.0952 ± 0.0025 | 0.02908 ± 0.00179 |
| ridge | 7.6567 ± 0.1662 | 0.6373 ± 0.3466 | 0.2116 ± 0.1922 | 0.11167 ± 0.00193 |
| neural_net_mlp_lbfgs | 12.2041 ± 19.2918 | 2.2654 ± 3.7422 | 0.3072 ± 0.3195 | 0.10897 ± 0.13727 |

## Caveat

Only 300 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
