# DD u3 Forecast XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_abd_v1/u3_forecast.joblib`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics_v2`
- Training theta1 range: -87.0 to 86.0 deg
- Training theta2 range: -85.0 to 89.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.
- Note: this explains the current theta/case feature model, not yet a physics-feature retrained model.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.3886 | 0.5806 | 0.0181 | 0.5673 |
| 2 | `d11` | 0.0512 | 0.0184 | 0.0631 | 0.0722 |
| 3 | `d12` | 0.0444 | 0.0779 | 0.0095 | 0.0457 |
| 4 | `d66` | 0.0432 | 0.0806 | 0.0086 | 0.0404 |
| 5 | `d11_d22_ratio` | 0.0416 | 0.0064 | 0.0979 | 0.0204 |
| 6 | `a11_a22_ratio` | 0.0404 | 0.0059 | 0.0987 | 0.0165 |
| 7 | `a11` | 0.0373 | 0.0127 | 0.0478 | 0.0515 |
| 8 | `bending_anisotropy` | 0.0316 | 0.0057 | 0.0801 | 0.0090 |
| 9 | `a12` | 0.0313 | 0.0566 | 0.0086 | 0.0288 |
| 10 | `a66` | 0.0307 | 0.0565 | 0.0077 | 0.0280 |

## Practical Reading

- High scalar importance means the feature strongly affects Pt, Max. Displacement, or Max. Force predictions.
- High type importance means the feature strongly affects u3 Type 2/3 classification.
- High curve importance means the feature strongly affects PCA curve-shape coefficients.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
