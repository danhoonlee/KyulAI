# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_goint_physics_nn_v2/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics_nn_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.0650 | 0.0559 | 0.0733 | 0.0658 |
| 2 | `a66_geom_ratio` | 0.0612 | 0.0391 | 0.0818 | 0.0627 |
| 3 | `angle_min_abs` | 0.0576 | 0.0594 | 0.0448 | 0.0686 |
| 4 | `d12` | 0.0355 | 0.0402 | 0.0367 | 0.0296 |
| 5 | `d11_d22_ratio` | 0.0312 | 0.0333 | 0.0347 | 0.0255 |
| 6 | `bending_anisotropy` | 0.0303 | 0.0351 | 0.0265 | 0.0293 |
| 7 | `d66` | 0.0288 | 0.0312 | 0.0274 | 0.0276 |
| 8 | `d11` | 0.0256 | 0.0252 | 0.0235 | 0.0282 |
| 9 | `b11_d11_ratio` | 0.0253 | 0.0233 | 0.0316 | 0.0212 |
| 10 | `abs_theta1` | 0.0251 | 0.0340 | 0.0231 | 0.0181 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
