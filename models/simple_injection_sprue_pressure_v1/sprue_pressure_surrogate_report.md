# Simple Injection Sprue Pressure Surrogate Report

Dataset: `data/datasets/Simple_Injection`

This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.
The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.

## Data

- Samples with results: 240
- Geometry groups represented: 24
- Process combinations represented: 10
- Curve sequence length: 128
- Input features used internally: 23

## Classical ML Validation

Best model: `hist_gradient_boosting`

| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |
|---|---:|---:|---:|---:|
| hist_gradient_boosting | 1.8886 ± 0.2245 | 0.1175 ± 0.0352 | 0.0951 ± 0.0050 | 0.02896 ± 0.00332 |
| extra_trees | 1.9187 ± 0.2088 | 0.0568 ± 0.0220 | 0.0966 ± 0.0080 | 0.02971 ± 0.00279 |
| random_forest | 1.9315 ± 0.2110 | 0.0578 ± 0.0345 | 0.0943 ± 0.0060 | 0.02971 ± 0.00305 |
| ridge | 7.7239 ± 0.3380 | 0.8625 ± 0.7546 | 0.2720 ± 0.3143 | 0.11207 ± 0.00313 |
| neural_net_mlp_lbfgs | 11.4473 ± 18.6450 | 1.3045 ± 1.6495 | 0.4028 ± 0.5181 | 0.13689 ± 0.20671 |

## Caveat

Only 240 of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.
Treat these metrics as a baseline and retrain after each new geometry batch is added.
