# Pt-Consistent Neural Challengers

## Protocol

- Development rows: 2151
- Locked Holdout rows: 549
- Split key: Case + theta1 + theta2 across all three panel sizes
- Existing GointMLP and Hybrid artifacts are preserved.
- Raw neural curve and Max. Force are not rescaled.
- Display P1 intercepts are solved so the two predicted P1 slopes intersect at predicted Pt.

## Locked Holdout

| Model | Type acc. | Pt MAE | Max force MAE | Curve force RMSE | Display P1 gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing 3-Size GointMLP | 0.9253 | 316.72 | 620.59 | 884.08 | N/A |
| Existing 3-Size Hybrid | 0.9617 | 205.48 | 433.85 | 699.49 | N/A |
| Pt-Consistent GointMLP v1 | 0.9271 | 272.92 | 652.46 | 875.53 | 0.0000 |
| Pt-Consistent Hybrid v1 | 0.9599 | 173.64 | 357.93 | 671.03 | 0.0000 |

## Interpretation

These are locked-Holdout challengers, not replacements for the current models. The neural heads learn Pt displacement and both P1 slopes in addition to the existing response outputs. The displayed P1 intersection is exact by construction, while the independently predicted response curve remains untouched.
