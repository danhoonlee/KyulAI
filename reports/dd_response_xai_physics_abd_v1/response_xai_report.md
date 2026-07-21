# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.2337 | 0.3997 | 0.0627 | 0.2388 |
| 2 | `d11` | 0.1221 | 0.1698 | 0.0861 | 0.1103 |
| 3 | `a11` | 0.0913 | 0.1195 | 0.0696 | 0.0849 |
| 4 | `bending_anisotropy` | 0.0713 | 0.0896 | 0.0763 | 0.0480 |
| 5 | `angle_abs_std` | 0.0550 | 0.0035 | 0.0308 | 0.1306 |
| 6 | `membrane_anisotropy` | 0.0522 | 0.0535 | 0.0682 | 0.0347 |
| 7 | `angle_max_abs` | 0.0490 | 0.0029 | 0.0418 | 0.1023 |
| 8 | `d11_d22_ratio` | 0.0425 | 0.0200 | 0.0730 | 0.0344 |
| 9 | `a11_a22_ratio` | 0.0345 | 0.0108 | 0.0669 | 0.0257 |
| 10 | `stack_balance_cos_sum` | 0.0309 | 0.0175 | 0.0579 | 0.0173 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
