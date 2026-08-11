# Pt-Consistent Deep Learning UQ v1

## Protocol

- Development rows: 2154
- Grouped OOF folds: 5
- Fixed benchmark rows: 546
- Fold models and fold-local Tree teachers never saw their assessment groups.
- Fold models used random initialization to avoid full-development warm-start leakage.
- Type calibration and interval conditioning were selected from development OOF only.
- Production models and endpoints were not changed.

## Point performance

| Model | Partition | Type acc. | Pt MAE | Max. Force MAE | Mean row Curve RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| goint | development_oof | 0.9457 | 821.60 | 1315.27 | 1127.53 |
| goint | fixed_benchmark | 0.9176 | 876.01 | 1361.00 | 1065.80 |
| hybrid | development_oof | 0.9485 | 412.60 | 633.18 | 515.83 |
| hybrid | fixed_benchmark | 0.9304 | 499.66 | 659.06 | 540.14 |

## Frozen UQ choices and 90% benchmark coverage

| Model | Type calibration | Pt interval | Pt coverage | Max. Force interval | Max. Force coverage |
| --- | --- | --- | ---: | --- | ---: |
| goint | temperature_scaling | geometry_case | 0.9359 | geometry_case | 0.8993 |
| hybrid | temperature_scaling | geometry_case | 0.8919 | geometry_case | 0.8956 |

## Interpretation

The OOF rows estimate model-family uncertainty without reusing the same Case+theta design for fitting and assessment. The final challengers were then trained on all development rows, and the reused fixed benchmark was opened only after the point-model and UQ choices were frozen.

These results remain engineering diagnostics. A new untouched simulation campaign is still required before publication-grade external validation claims.
