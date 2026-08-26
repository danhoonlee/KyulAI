# Laminate Forecast XAI Report

- Model: `models/dd_laminate_response_hybrid_student_canonical_v2/response_goint.pt`
- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Samples: 1800
- Feature set: `theta_physics_geometry_canonical_v2`
- Training theta1 range: -89.0 to 90.0 deg
- Training theta2 range: -89.0 to 90.0 deg
- Method: GointMLP occlusion sensitivity + finite-difference local sensitivity.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_abs_std` | 0.1442 | 0.0954 | 0.2150 | 0.1223 |
| 2 | `angle_min_abs` | 0.1040 | 0.0786 | 0.1375 | 0.0959 |
| 3 | `d11_d22_ratio` | 0.0512 | 0.0426 | 0.0778 | 0.0332 |
| 4 | `a11_a22_ratio` | 0.0491 | 0.0404 | 0.0749 | 0.0320 |
| 5 | `a12` | 0.0352 | 0.0398 | 0.0268 | 0.0390 |
| 6 | `a66` | 0.0345 | 0.0411 | 0.0235 | 0.0389 |
| 7 | `d66` | 0.0334 | 0.0382 | 0.0252 | 0.0367 |
| 8 | `d12` | 0.0326 | 0.0367 | 0.0244 | 0.0366 |
| 9 | `panel_b_in` | 0.0313 | 0.0338 | 0.0297 | 0.0303 |
| 10 | `d22` | 0.0307 | 0.0402 | 0.0163 | 0.0356 |

## Generated Artifacts

- `response_feature_importance.csv`
- `response_local_sensitivity.csv`
