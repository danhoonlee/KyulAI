# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_goint_physics_xai_v2/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Samples: 900
- Feature set: `theta_physics_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.1053 | 0.1037 | 0.1117 | 0.1005 |
| 2 | `angle_min_abs` | 0.0947 | 0.1133 | 0.0791 | 0.0919 |
| 3 | `abs_theta1` | 0.0588 | 0.0755 | 0.0694 | 0.0314 |
| 4 | `d11_d22_ratio` | 0.0450 | 0.0425 | 0.0582 | 0.0343 |
| 5 | `d12` | 0.0335 | 0.0344 | 0.0318 | 0.0342 |
| 6 | `angle_max_abs` | 0.0329 | 0.0279 | 0.0407 | 0.0302 |
| 7 | `bending_anisotropy` | 0.0326 | 0.0297 | 0.0282 | 0.0400 |
| 8 | `a11_a22_ratio` | 0.0324 | 0.0391 | 0.0330 | 0.0252 |
| 9 | `d66` | 0.0306 | 0.0333 | 0.0278 | 0.0308 |
| 10 | `abs_theta2` | 0.0298 | 0.0382 | 0.0287 | 0.0225 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
