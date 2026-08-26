# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_geometry_tree_canonical_v2/response_surrogate.joblib`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Feature set: `theta_physics_geometry_canonical_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.1500 | 0.2665 | 0.0520 | 0.1315 |
| 2 | `a11` | 0.1063 | 0.1281 | 0.0826 | 0.1080 |
| 3 | `d11` | 0.1047 | 0.1287 | 0.0828 | 0.1028 |
| 4 | `panel_aspect` | 0.0603 | 0.1093 | 0.0143 | 0.0574 |
| 5 | `membrane_anisotropy` | 0.0584 | 0.0604 | 0.0699 | 0.0449 |
| 6 | `bending_anisotropy` | 0.0573 | 0.0555 | 0.0734 | 0.0431 |
| 7 | `angle_abs_std` | 0.0428 | 0.0029 | 0.0269 | 0.0987 |
| 8 | `stack_balance_cos_sum` | 0.0419 | 0.0256 | 0.0652 | 0.0349 |
| 9 | `d11_d22_ratio` | 0.0398 | 0.0076 | 0.0740 | 0.0379 |
| 10 | `a11_a22_ratio` | 0.0386 | 0.0123 | 0.0656 | 0.0380 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
