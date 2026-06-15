# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_goint_physics_xai_v1/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.0599 | 0.0618 | 0.0542 | 0.0638 |
| 2 | `a66_geom_ratio` | 0.0599 | 0.0457 | 0.0619 | 0.0721 |
| 3 | `angle_min_abs` | 0.0524 | 0.0596 | 0.0326 | 0.0650 |
| 4 | `a12` | 0.0323 | 0.0361 | 0.0284 | 0.0325 |
| 5 | `abs_theta1` | 0.0286 | 0.0353 | 0.0271 | 0.0232 |
| 6 | `membrane_anisotropy` | 0.0260 | 0.0251 | 0.0282 | 0.0245 |
| 7 | `b11` | 0.0259 | 0.0227 | 0.0363 | 0.0187 |
| 8 | `b11_d11_ratio` | 0.0248 | 0.0230 | 0.0296 | 0.0218 |
| 9 | `b22_d22_ratio` | 0.0246 | 0.0197 | 0.0364 | 0.0177 |
| 10 | `bending_anisotropy` | 0.0240 | 0.0230 | 0.0277 | 0.0212 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
