# DD u3 Forecast XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_v1/u3_forecast.joblib`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics`
- Training theta1 range: -87.0 to 86.0 deg
- Training theta2 range: -85.0 to 89.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.
- Note: this explains the physics-feature retrained model.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.3933 | 0.5924 | 0.0139 | 0.5736 |
| 2 | `d11` | 0.0444 | 0.0170 | 0.0513 | 0.0648 |
| 3 | `a11_a22_ratio` | 0.0400 | 0.0061 | 0.0990 | 0.0150 |
| 4 | `a11` | 0.0397 | 0.0118 | 0.0581 | 0.0494 |
| 5 | `d12` | 0.0388 | 0.0727 | 0.0076 | 0.0362 |
| 6 | `d11_d22_ratio` | 0.0359 | 0.0061 | 0.0807 | 0.0210 |
| 7 | `d66` | 0.0345 | 0.0630 | 0.0078 | 0.0327 |
| 8 | `bending_anisotropy` | 0.0315 | 0.0047 | 0.0807 | 0.0089 |
| 9 | `a12` | 0.0304 | 0.0569 | 0.0061 | 0.0282 |
| 10 | `a66` | 0.0299 | 0.0548 | 0.0068 | 0.0280 |

## Practical Reading

- High scalar importance means the feature strongly affects Pt, Max. Displacement, or Max. Force predictions.
- High type importance means the feature strongly affects u3 Type 2/3 classification.
- High curve importance means the feature strongly affects PCA curve-shape coefficients.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
