# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Feature set: `theta_physics_geometry_v1`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.1999 | 0.3643 | 0.0626 | 0.1729 |
| 2 | `d11` | 0.1020 | 0.1285 | 0.0786 | 0.0989 |
| 3 | `a11` | 0.0804 | 0.0945 | 0.0708 | 0.0760 |
| 4 | `bending_anisotropy` | 0.0616 | 0.0619 | 0.0775 | 0.0455 |
| 5 | `panel_aspect` | 0.0588 | 0.1093 | 0.0142 | 0.0530 |
| 6 | `angle_abs_std` | 0.0491 | 0.0043 | 0.0342 | 0.1087 |
| 7 | `angle_max_abs` | 0.0476 | 0.0020 | 0.0440 | 0.0968 |
| 8 | `d11_d22_ratio` | 0.0439 | 0.0085 | 0.0764 | 0.0466 |
| 9 | `membrane_anisotropy` | 0.0398 | 0.0313 | 0.0636 | 0.0247 |
| 10 | `a11_a22_ratio` | 0.0347 | 0.0087 | 0.0620 | 0.0335 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
