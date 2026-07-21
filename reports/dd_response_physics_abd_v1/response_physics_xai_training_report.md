# Laminate Forecast ABD-Normalized Physics XAI Training Report

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- ABD normalization: `A* = A / h`, `B* = 2B / h^2`, `D* = 12D / h^3`
- Active API keys: `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`

## Machine Learning

- Model path: `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
- Feature set: `theta_physics_v2`
- Samples: 900
- Input features: 35
- Type accuracy: 0.9422 +/- 0.0156
- Type macro F1: 0.9372 +/- 0.0154
- Pt MAE: 438.11 kips
- Curve normalized RMSE: 0.00697

## Deep Learning

- Model path: `models/dd_laminate_response_goint_physics_nn_abd_v1/response_goint.pt`
- Feature set: `theta_physics_nn_v2`
- Samples: 900
- Input features: 47
- Type accuracy: 0.9389 +/- 0.0111
- Type macro F1: 0.9383 +/- 0.0121
- Pt MAE: 661.41 kips
- Curve normalized RMSE: 0.02131

## XAI Artifacts

- `reports/dd_response_xai_physics_abd_v1`
- `reports/dd_response_xai_goint_physics_nn_abd_v1`
