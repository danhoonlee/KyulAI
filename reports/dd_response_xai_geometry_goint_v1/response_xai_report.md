# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_geometry_goint_v1/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Feature set: `theta_physics_geometry_v1`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.0815 | 0.0711 | 0.1041 | 0.0693 |
| 2 | `angle_abs_std` | 0.0811 | 0.0626 | 0.1037 | 0.0771 |
| 3 | `panel_aspect` | 0.0505 | 0.0854 | 0.0316 | 0.0345 |
| 4 | `b_slenderness` | 0.0464 | 0.0709 | 0.0362 | 0.0321 |
| 5 | `panel_b_in` | 0.0460 | 0.0735 | 0.0327 | 0.0319 |
| 6 | `abs_theta1` | 0.0446 | 0.0515 | 0.0531 | 0.0292 |
| 7 | `d66` | 0.0298 | 0.0279 | 0.0309 | 0.0306 |
| 8 | `d12` | 0.0283 | 0.0312 | 0.0284 | 0.0255 |
| 9 | `d11_d22_ratio` | 0.0283 | 0.0275 | 0.0336 | 0.0237 |
| 10 | `angle_max_abs` | 0.0279 | 0.0221 | 0.0315 | 0.0299 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
