# DD u3 Forecast GointMLP XAI Report

- Model: `models/dd_laminate_u3_forecast_physics_v1/u3_forecast_goint.pt`
- Manifest: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics`
- Method: GointMLP feature occlusion sensitivity + finite-difference local sensitivity.
- Note: type probability is still supplied by the sibling Tree classifier; this report explains the GointMLP Pt/max/curve heads.

## Top Global Drivers

| Rank | Feature | Combined | Scalar | Type | Curve |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `angle_min_abs` | 0.0854 | 0.0870 | 0.0000 | 0.0837 |
| 2 | `angle_abs_std` | 0.0446 | 0.0432 | 0.0000 | 0.0459 |
| 3 | `a66_geom_ratio` | 0.0389 | 0.0367 | 0.0000 | 0.0411 |
| 4 | `theta2_cos_4` | 0.0349 | 0.0365 | 0.0000 | 0.0333 |
| 5 | `theta1_cos_4` | 0.0299 | 0.0301 | 0.0000 | 0.0298 |
| 6 | `bending_anisotropy` | 0.0269 | 0.0268 | 0.0000 | 0.0271 |
| 7 | `theta2_cos_2` | 0.0261 | 0.0291 | 0.0000 | 0.0232 |
| 8 | `b22_d22_ratio` | 0.0255 | 0.0261 | 0.0000 | 0.0250 |
| 9 | `b11_d11_ratio` | 0.0251 | 0.0250 | 0.0000 | 0.0252 |
| 10 | `d12` | 0.0248 | 0.0247 | 0.0000 | 0.0249 |

## Practical Reading

- Importance is measured by masking one normalized input feature to its training mean.
- High scalar importance means the GointMLP Pt, Max. Displacement, or Max. Force heads move strongly when the feature is hidden.
- High curve importance means the GointMLP curve head moves strongly when the feature is hidden.
- Local sensitivity is reported as predicted Pt change per degree around representative training points.

## Generated Artifacts

- `u3_feature_importance.csv`
- `u3_local_sensitivity.csv`
