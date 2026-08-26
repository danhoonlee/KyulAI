# DD u3 Forecast GointMLP XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_canonical_v2/u3_forecast_goint.pt`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics_compact_canonical_v2`
- Method: GointMLP feature occlusion sensitivity + finite-difference local sensitivity.
- Note: type probability is still supplied by the sibling Tree classifier; this report explains the GointMLP Pt/max/curve heads.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.1248 | 0.1216 | 0.0000 | 0.1281 |
| 2 | `angle_abs_std` | 0.0705 | 0.0685 | 0.0000 | 0.0724 |
| 3 | `a12` | 0.0346 | 0.0344 | 0.0000 | 0.0347 |
| 4 | `d12` | 0.0298 | 0.0322 | 0.0000 | 0.0274 |
| 5 | `d66` | 0.0294 | 0.0281 | 0.0000 | 0.0307 |
| 6 | `angle_abs_mean` | 0.0291 | 0.0312 | 0.0000 | 0.0269 |
| 7 | `stack_balance_cos_sum` | 0.0290 | 0.0290 | 0.0000 | 0.0291 |
| 8 | `d11` | 0.0271 | 0.0291 | 0.0000 | 0.0251 |
| 9 | `theta2_cos_2` | 0.0260 | 0.0288 | 0.0000 | 0.0233 |
| 10 | `theta2_sin_4` | 0.0248 | 0.0253 | 0.0000 | 0.0242 |

## Practical Reading

- Importance is measured by masking one normalized input feature to its training mean.
- High scalar importance means the GointMLP Pt, Max. Displacement, or Max. Force heads move strongly when the feature is hidden.
- High curve importance means the GointMLP curve head moves strongly when the feature is hidden.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
