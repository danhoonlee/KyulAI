# DD u3 Forecast XAI Report

- Model: `models/dd_laminate_u3_forecast_v2/u3_forecast.joblib`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Training theta1 range: -87.0 to 86.0 deg
- Training theta2 range: -85.0 to 89.0 deg
- Method: tree ensemble feature importance + finite-difference local sensitivity.
- Note: this explains the current theta/case feature model, not yet a physics-feature retrained model.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `theta1_cos_2` | 0.1496 | 0.1525 | 0.1328 | 0.1634 |
| 2 | `theta2_cos_4` | 0.1389 | 0.2249 | 0.0412 | 0.1507 |
| 3 | `theta2_cos_2` | 0.1346 | 0.1154 | 0.1328 | 0.1555 |
| 4 | `abs_theta1` | 0.1313 | 0.1350 | 0.1098 | 0.1492 |
| 5 | `abs_theta2` | 0.1197 | 0.1072 | 0.1060 | 0.1459 |
| 6 | `theta1_cos_4` | 0.1055 | 0.1604 | 0.0342 | 0.1219 |
| 7 | `theta_abs_diff` | 0.0611 | 0.0162 | 0.1440 | 0.0231 |
| 8 | `theta_product` | 0.0545 | 0.0506 | 0.0607 | 0.0523 |
| 9 | `theta_diff` | 0.0204 | 0.0038 | 0.0535 | 0.0039 |
| 10 | `theta1` | 0.0175 | 0.0082 | 0.0360 | 0.0082 |

## Practical Reading

- High scalar importance means the feature strongly affects Pt, Max. Displacement, or Max. Force predictions.
- High type importance means the feature strongly affects u3 Type 2/3 classification.
- High curve importance means the feature strongly affects PCA curve-shape coefficients.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
