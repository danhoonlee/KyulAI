# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_physics_xai_v1/response_surrogate.joblib`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.2256 | 0.3841 | 0.0547 | 0.2379 |
| 2 | `d11` | 0.1203 | 0.1740 | 0.0778 | 0.1090 |
| 3 | `a11` | 0.0913 | 0.1257 | 0.0671 | 0.0810 |
| 4 | `bending_anisotropy` | 0.0639 | 0.0810 | 0.0674 | 0.0433 |
| 5 | `membrane_anisotropy` | 0.0497 | 0.0566 | 0.0597 | 0.0328 |
| 6 | `angle_abs_std` | 0.0491 | 0.0030 | 0.0251 | 0.1193 |
| 7 | `angle_max_abs` | 0.0420 | 0.0025 | 0.0407 | 0.0827 |
| 8 | `d11_d22_ratio` | 0.0400 | 0.0167 | 0.0651 | 0.0383 |
| 9 | `a11_a22_ratio` | 0.0333 | 0.0105 | 0.0599 | 0.0295 |
| 10 | `stack_balance_cos_sum` | 0.0276 | 0.0156 | 0.0482 | 0.0191 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
