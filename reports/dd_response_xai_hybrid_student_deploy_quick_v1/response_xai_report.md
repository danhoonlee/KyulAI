# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_hybrid_student_deploy_quick_v1/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.1010 | 0.0866 | 0.1059 | 0.1107 |
| 2 | `angle_min_abs` | 0.0895 | 0.1066 | 0.0753 | 0.0865 |
| 3 | `abs_theta1` | 0.0487 | 0.0618 | 0.0572 | 0.0270 |
| 4 | `a66` | 0.0478 | 0.0446 | 0.0462 | 0.0525 |
| 5 | `d66` | 0.0375 | 0.0429 | 0.0352 | 0.0345 |
| 6 | `bending_anisotropy` | 0.0367 | 0.0413 | 0.0311 | 0.0377 |
| 7 | `a11_a22_ratio` | 0.0365 | 0.0396 | 0.0420 | 0.0279 |
| 8 | `d11_d22_ratio` | 0.0364 | 0.0352 | 0.0463 | 0.0277 |
| 9 | `angle_max_abs` | 0.0336 | 0.0279 | 0.0413 | 0.0315 |
| 10 | `a12` | 0.0332 | 0.0377 | 0.0271 | 0.0349 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
