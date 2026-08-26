# Pt-Consistent Neural Challengers

## Protocol

- Development rows: 2154
- Locked Holdout rows: 546
- Split key: Case + theta1 + theta2 across all three panel sizes
- Existing GointMLP and Hybrid artifacts are preserved.
- Raw neural curve and Max. Force are not rescaled.
- Display P1 intercepts are solved so the two predicted P1 slopes intersect at predicted Pt.

## Locked Holdout

| Model | Type acc. | Pt MAE | Max force MAE | Curve force RMSE | Display P1 gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing 3-Size GointMLP | 0.9048 | 532.84 | 1011.54 | 1017.90 | N/A |
| Existing 3-Size Hybrid | 0.9341 | 305.64 | 389.45 | 438.50 | N/A |
| Pt-Consistent GointMLP v1 | 0.9139 | 525.37 | 867.40 | 908.29 | 0.0000 |
| Pt-Consistent Hybrid v1 | 0.9322 | 286.66 | 362.38 | 425.62 | 0.0000 |

## Interpretation

These are locked-Holdout challengers, not replacements for the current models. The neural heads learn Pt displacement and both P1 slopes in addition to the existing response outputs. The displayed P1 intersection is exact by construction, while the independently predicted response curve remains untouched.
