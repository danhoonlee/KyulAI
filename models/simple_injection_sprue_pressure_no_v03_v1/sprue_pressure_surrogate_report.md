# Simple Injection Sprue Pressure Surrogate Report

Dataset: `/tmp/kyulai_simple_injection_no_v03`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 320
- Geometry groups represented: 34
- Process combinations represented: 15
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `extra_trees`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| extra_trees | 2.2489 ± 0.0848 | 0.0784 ± 0.0199 | 0.0961 ± 0.0030 | 0.03347 ± 0.00073 |
| hist_gradient_boosting | 2.4624 ± 0.2234 | 0.3003 ± 0.0561 | 0.1305 ± 0.0224 | 0.03609 ± 0.00171 |
| random_forest | 2.5231 ± 0.6047 | 0.1505 ± 0.0642 | 0.1102 ± 0.0214 | 0.03572 ± 0.00518 |
| neural_net_mlp_lbfgs | 7.3006 ± 5.0202 | 5.1107 ± 6.0454 | 0.5452 ± 0.5494 | 0.07491 ± 0.03186 |
| ridge | 9.6602 ± 1.1596 | 1.0007 ± 0.0723 | 1.1408 ± 1.2184 | 0.13901 ± 0.01900 |

## Shape-Oriented Metrics

| Model | Shape corr ↑ | Norm AUC MAE ↓ | Pressure-time AUC MAE (MPa*s) ↓ | Peak position MAE ↓ | Rise slope MAE ↓ |
|---|---:|---:|---:|---:|---:|
| extra_trees | 0.9972 ± 0.0002 | 0.00604 ± 0.00045 | 8.2288 ± 0.2583 | 0.09372 ± 0.00164 | 3.6337 ± 2.5412 |
| hist_gradient_boosting | 0.9969 ± 0.0003 | 0.00731 ± 0.00057 | 9.7459 ± 0.4742 | 0.08169 ± 0.00484 | 3.8857 ± 2.7664 |
| random_forest | 0.9965 ± 0.0011 | 0.00571 ± 0.00009 | 8.2583 ± 0.9001 | 0.09020 ± 0.00254 | 3.7943 ± 2.7999 |
| neural_net_mlp_lbfgs | 0.9796 ± 0.0227 | 0.01443 ± 0.00384 | 32.7536 ± 21.0298 | 0.09325 ± 0.00590 | 4.6060 ± 2.6009 |
| ridge | 0.9364 ± 0.0222 | 0.03577 ± 0.00354 | 49.0909 ± 2.4894 | 0.04490 ± 0.00249 | 8.9872 ± 2.8988 |

## Caveat

Only 320 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
