# DD u3 Forecast GointMLP XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_v3/u3_forecast_goint.pt`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics_v2`
- Method: GointMLP feature occlusion sensitivity + finite-difference local sensitivity.
- Note: type probability is still supplied by the sibling Tree classifier; this report explains the GointMLP Pt/max/curve heads.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.1389 | 0.1370 | 0.0000 | 0.1408 |
| 2 | `angle_abs_std` | 0.0706 | 0.0687 | 0.0000 | 0.0725 |
| 3 | `theta1_cos_4` | 0.0467 | 0.0497 | 0.0000 | 0.0437 |
| 4 | `theta2_cos_4` | 0.0381 | 0.0402 | 0.0000 | 0.0359 |
| 5 | `d12` | 0.0337 | 0.0353 | 0.0000 | 0.0322 |
| 6 | `theta1_cos_2` | 0.0301 | 0.0338 | 0.0000 | 0.0264 |
| 7 | `abs_theta1` | 0.0300 | 0.0345 | 0.0000 | 0.0255 |
| 8 | `abs_theta2` | 0.0273 | 0.0313 | 0.0000 | 0.0232 |
| 9 | `a12` | 0.0268 | 0.0253 | 0.0000 | 0.0283 |
| 10 | `bending_anisotropy` | 0.0254 | 0.0252 | 0.0000 | 0.0256 |

## Practical Reading

- Importance is measured by masking one normalized input feature to its training mean.
- High scalar importance means the GointMLP Pt, Max. Displacement, or Max. Force heads move strongly when the feature is hidden.
- High curve importance means the GointMLP curve head moves strongly when the feature is hidden.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
