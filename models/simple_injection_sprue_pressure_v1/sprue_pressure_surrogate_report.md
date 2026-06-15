# Simple Injection Sprue Pressure Surrogate Report

Dataset: `data/datasets/Simple_Injection`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 360
- Geometry groups represented: 42
- Process combinations represented: 20
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| extra_trees | 2.5553 ± 0.1725 | 0.0651 ± 0.0271 | 0.0975 ± 0.0024 | 0.03795 ± 0.00186 |
| random_forest | 2.8563 ± 0.3843 | 0.1655 ± 0.0457 | 0.1230 ± 0.0174 | 0.04281 ± 0.00670 |
| hist_gradient_boosting | 3.1420 ± 0.6630 | 0.2400 ± 0.0192 | 0.1165 ± 0.0195 | 0.04710 ± 0.01094 |
| neural_net_mlp_lbfgs | 5.6134 ± 3.3988 | 3.2233 ± 2.8286 | 0.2914 ± 0.0776 | 0.07215 ± 0.03405 |
| ridge | 10.2206 ± 0.7320 | 2.5036 ± 0.3456 | 1.0493 ± 0.2470 | 0.14868 ± 0.00940 |

## Shape-Oriented Metrics

| Model | Shape corr ↑ | Norm AUC MAE ↓ | Pressure-time AUC MAE (MPa*s) ↓ | Peak position MAE ↓ | Rise slope MAE ↓ |
|---|---:|---:|---:|---:|---:|
| extra_trees | 0.9965 ± 0.0003 | 0.00723 ± 0.00101 | 9.8598 ± 1.3789 | 0.06566 ± 0.00731 | 6.8043 ± 2.2320 |
| random_forest | 0.9949 ± 0.0019 | 0.00822 ± 0.00094 | 11.4157 ± 1.3290 | 0.06682 ± 0.00205 | 7.2177 ± 2.3275 |
| hist_gradient_boosting | 0.9942 ± 0.0030 | 0.00974 ± 0.00189 | 13.4787 ± 2.3597 | 0.05739 ± 0.00936 | 7.7597 ± 3.4079 |
| neural_net_mlp_lbfgs | 0.9800 ± 0.0216 | 0.01430 ± 0.00543 | 18.9045 ± 3.5505 | 0.06984 ± 0.00562 | 7.4493 ± 1.4735 |
| ridge | 0.9278 ± 0.0076 | 0.03711 ± 0.00331 | 54.5057 ± 7.0431 | 0.03834 ± 0.00439 | 12.5478 ± 2.4194 |

## Caveat

Only 360 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
