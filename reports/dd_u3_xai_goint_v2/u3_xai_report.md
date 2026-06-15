# DD u3 Forecast GointMLP XAI Report

- Model: `models/dd_laminate_u3_forecast_v2/u3_forecast_goint.pt`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta`
- Method: GointMLP feature occlusion sensitivity + finite-difference local sensitivity.
- Note: type probability is still supplied by the sibling Tree classifier; this report explains the GointMLP Pt/max/curve heads.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `theta2_cos_4` | 0.1673 | 0.1657 | 0.0000 | 0.1688 |
| 2 | `theta1_cos_4` | 0.1586 | 0.1606 | 0.0000 | 0.1567 |
| 3 | `abs_theta1` | 0.0837 | 0.0888 | 0.0000 | 0.0786 |
| 4 | `theta2_cos_2` | 0.0824 | 0.0866 | 0.0000 | 0.0783 |
| 5 | `abs_theta2` | 0.0813 | 0.0875 | 0.0000 | 0.0751 |
| 6 | `theta1_cos_2` | 0.0750 | 0.0797 | 0.0000 | 0.0703 |
| 7 | `theta2_sin_4` | 0.0452 | 0.0462 | 0.0000 | 0.0442 |
| 8 | `theta1_sin_4` | 0.0420 | 0.0441 | 0.0000 | 0.0398 |
| 9 | `theta_product` | 0.0351 | 0.0296 | 0.0000 | 0.0406 |
| 10 | `theta_abs_diff` | 0.0316 | 0.0272 | 0.0000 | 0.0361 |

## Practical Reading

- Importance is measured by masking one normalized input feature to its training mean.
- High scalar importance means the GointMLP Pt, Max. Displacement, or Max. Force heads move strongly when the feature is hidden.
- High curve importance means the GointMLP curve head moves strongly when the feature is hidden.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
