# DD Laminate Three-Geometry Validation Summary

## Objective

This validation separates two different generalization questions:

1. Can the model predict unseen `Case + theta1 + theta2` designs within the supported 6x4, 6x8, and 8x8 panel sizes?
2. Can the model transfer to a panel size that was completely absent during training?

One permanent grouped holdout answers the first question. Leave-one-geometry-out evaluation inside the development partition answers the second.

## Data And Split

- Total: 2,700 rows / 900 unique design groups
- Geometries: 6x4, 6x8, and 8x8, with 900 rows per geometry
- Development: 2,154 rows / 718 design groups / 718 rows per geometry
- Locked holdout: 546 rows / 182 design groups / 182 rows per geometry
- Group key: `Case + theta1 + theta2`
- Group leakage: 0
- Split manifest SHA-256: `af7b4b020abc943c2ff3b942f7b696c9691d7ca796b686c5fdfeba28d8151ed6`
- Protocol summary SHA-256: `f395477e6f6280c870391613f76f1a810b2d771e739db042b9d4e2d19bef16fd`

The same design group is assigned to the same partition at every panel size. The locked groups were also excluded from synthetic distillation samples.

## Grouped Cross-Validation

Five-fold grouped CV was run only on the 2,154-row development partition.

| Model | Type accuracy | Macro F1 | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tree + Physics XAI | 0.9461 | 0.9424 | **176.51** | **212.23** | **0.00562** | **529.88** |
| GointMLP + Physics XAI | 0.9536 | 0.9515 | 641.09 | 1,114.75 | 0.01759 | 1,112.53 |
| Hybrid Teacher-Student | **0.9582** | **0.9550** | 365.67 | 612.15 | 0.00965 | 685.48 |

The Hybrid has the best Type classification result. The Tree model is substantially better for Pt and curve regression.

## Locked Holdout

The saved final artifacts, trained on the development partition, were evaluated on the 546 locked rows.

| Model | Pseudo-Type agreement | Macro F1 | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tree + Physics XAI | **0.9377** | **0.9347** | **190.12** | **153.70** | **0.00596** | **291.36** |
| GointMLP + Physics XAI | 0.9048 | 0.9021 | 532.84 | 1,011.54 | 0.01549 | 1,017.90 |
| Hybrid Teacher-Student | 0.9341 | 0.9303 | 305.64 | 389.45 | 0.00649 | 438.50 |

For the current product goal, the Tree model is the recommended release candidate because Pt and response-curve quality are the primary outputs. The Hybrid remains a useful challenger when Type accuracy, compact neural inference, or teacher-student research is the priority.

## Leave-One-Geometry-Out Transfer

Each experiment used only the development partition, trained on two geometries, and tested on the third geometry. These are transfer benchmarks, not release-holdout results.

| Held geometry | Model | Type accuracy | Pt MAE | Curve norm RMSE |
| --- | --- | ---: | ---: | ---: |
| 6x4 | Tree | **0.8649** | **9,828.99** | **0.03110** |
| 6x4 | GointMLP | 0.6017 | 10,362.35 | 0.04600 |
| 6x4 | Hybrid | 0.4944 | 9,950.89 | 0.04406 |
| 6x8 | Tree | 0.7897 | 1,393.86 | **0.01462** |
| 6x8 | GointMLP | 0.8747 | 1,009.84 | 0.03002 |
| 6x8 | Hybrid | **0.9457** | **884.15** | 0.02250 |
| 8x8 | Tree | **0.7897** | **3,643.59** | 0.02210 |
| 8x8 | GointMLP | 0.6643 | 7,569.93 | 0.03624 |
| 8x8 | Hybrid | 0.6448 | 3,821.11 | **0.02007** |

The 6x8 fold is interpolation between observed geometry conditions and performs best. Holding out 6x4 or 8x8 requires extrapolation beyond the training geometry range, and Pt performance degrades sharply. The current model should therefore be presented as supporting the three trained panel sizes, not arbitrary unseen panel dimensions.

## Serving Post-Processing Finding

The current web/app prediction path applies monotonic smoothing and `Pt-curve consistency` after inference. It preserves predicted Pt by rescaling the curve's max force until the fitted kink reaches Pt. On the locked holdout, that operation increases max-force MAE to roughly 7,800-9,700 and curve-force RMSE to roughly 10,900-13,200.

Raw surrogate quality and serving-consistent quality are now reported separately in `locked_artifact_eval/external_geometry_metrics.json`. The release UI should not use force rescaling as the long-term method for matching Pt and curve intersection; a Pt-consistent curve model or a constrained local fit that preserves force scale is required.

## Label And Scientific-Use Caveats

- Pt and force-displacement curves are direct targets from the delivered files.
- 6x4 Type labels are curated. The 6x8 and 8x8 Type labels include Curve CSV classifier pseudo-labels, so their Type scores are agreement metrics until manual review.
- The grouped split is now frozen and reproducible. However, earlier exploratory work used related 6x4/6x8 rows before this strict protocol was established. Treat this as the stable release regression gate, not as a pristine never-observed publication benchmark.
- A genuinely new fourth panel size is still required to claim generalization to unseen geometry.

## Artifacts

- Tree: `models/dd_laminate_response_geometry_tree_3size_grouped_v1/response_surrogate.joblib`
  - SHA-256: `5a1bc87048056cbf0afa2f2ed18d8aa230d65c7af0980535e3570d8475001c87`
- GointMLP: `models/dd_laminate_response_geometry_goint_3size_grouped_v1/response_goint.pt`
  - SHA-256: `045e052f72c38a3efb949c610b8fc6e422174016c5a77bd81ecb524af43c3551`
- Hybrid: `models/dd_laminate_response_hybrid_student_3size_grouped_v1/response_goint.pt`
  - SHA-256: `878e0988a054eec16f2d19010d421c47a15b221b3eba0abc227567b5b8e10630`
- Locked artifact metrics: `reports/dd_response_geometry_3size_grouped_v1/locked_artifact_eval/external_geometry_metrics.json`
- Geometry transfer metrics: `reports/dd_response_geometry_3size_grouped_v1/fixed_holdout_and_geometry_loo/fixed_holdout_metrics.json`
