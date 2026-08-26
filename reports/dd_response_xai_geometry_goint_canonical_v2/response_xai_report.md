# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_geometry_goint_canonical_v2/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Feature set: `theta_physics_geometry_canonical_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.1042 | 0.0709 | 0.1522 | 0.0894 |
| 2 | `panel_b_in` | 0.0629 | 0.0864 | 0.0623 | 0.0401 |
| 3 | `angle_min_abs` | 0.0575 | 0.0478 | 0.0713 | 0.0533 |
| 4 | `b_slenderness` | 0.0530 | 0.0885 | 0.0371 | 0.0334 |
| 5 | `panel_aspect` | 0.0452 | 0.0714 | 0.0370 | 0.0272 |
| 6 | `angle_max_abs` | 0.0343 | 0.0256 | 0.0466 | 0.0308 |
| 7 | `a12` | 0.0304 | 0.0369 | 0.0236 | 0.0306 |
| 8 | `theta_abs_diff` | 0.0301 | 0.0226 | 0.0362 | 0.0315 |
| 9 | `a11_a22_ratio` | 0.0264 | 0.0247 | 0.0267 | 0.0277 |
| 10 | `a66` | 0.0252 | 0.0303 | 0.0141 | 0.0312 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
