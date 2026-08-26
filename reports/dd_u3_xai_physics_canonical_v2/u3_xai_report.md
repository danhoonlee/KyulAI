# DD u3 Forecast XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_canonical_v2/u3_forecast.joblib`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics_compact_canonical_v2`
- Training theta1 range: -87.0 to 86.0 deg
- Training theta2 range: -85.0 to 89.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.
- Note: this explains the current theta/case feature model, not yet a physics-feature retrained model.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.3251 | 0.4863 | 0.0134 | 0.4757 |
| 2 | `a11` | 0.0748 | 0.0540 | 0.0641 | 0.1061 |
| 3 | `d11` | 0.0740 | 0.0521 | 0.0660 | 0.1038 |
| 4 | `d12` | 0.0473 | 0.0822 | 0.0131 | 0.0467 |
| 5 | `a66` | 0.0468 | 0.0805 | 0.0102 | 0.0497 |
| 6 | `d66` | 0.0434 | 0.0756 | 0.0099 | 0.0447 |
| 7 | `a12` | 0.0421 | 0.0693 | 0.0116 | 0.0453 |
| 8 | `a11_a22_ratio` | 0.0382 | 0.0085 | 0.0941 | 0.0120 |
| 9 | `d11_d22_ratio` | 0.0376 | 0.0079 | 0.0907 | 0.0142 |
| 10 | `bending_anisotropy` | 0.0335 | 0.0123 | 0.0755 | 0.0127 |

## Practical Reading

- High scalar importance means the feature strongly affects Pt, Max. Displacement, or Max. Force predictions.
- High type importance means the feature strongly affects u3 Type 2/3 classification.
- High curve importance means the feature strongly affects PCA curve-shape coefficients.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
