# Pt-Consistent Deep Learning UQ: 20260811-uq-deep-fold-pretrain-v2

## Protocol

- Development rows: 2154
- Grouped OOF folds: 5
- Fixed benchmark rows: 546
- Fold models and fold-local Tree teachers never saw their assessment groups.
- Fold models used random initialization to avoid full-development warm-start leakage.
- Training strategy: fold-local response pretraining followed by Pt-consistent fine-tuning.
- Type calibration and interval conditioning were selected from development OOF only.
- Production models and endpoints were not changed.

## Point performance

| Model | Partition | Type acc. | Pt MAE | Max. Force MAE | Mean row Curve RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| goint | development_oof | 0.9443 | 753.43 | 1157.58 | 931.25 |
| goint | fixed_benchmark | 0.9194 | 766.17 | 1077.71 | 852.75 |
| hybrid | development_oof | 0.9517 | 391.56 | 652.31 | 507.98 |
| hybrid | fixed_benchmark | 0.9322 | 411.74 | 660.35 | 492.31 |

## Frozen UQ choices and 90% benchmark coverage

| Model | Type calibration | Pt interval | Pt coverage | Max. Force interval | Max. Force coverage |
| --- | --- | --- | ---: | --- | ---: |
| goint | temperature_scaling | geometry_case | 0.9341 | geometry | 0.9231 |
| hybrid | temperature_scaling | geometry_case | 0.9212 | geometry_case | 0.9121 |

## Interpretation

The OOF rows estimate model-family uncertainty without reusing the same Case+theta design for fitting and assessment. The final challengers were then trained on all development rows, and the reused fixed benchmark was opened only after the point-model and UQ choices were frozen.

These results remain engineering diagnostics. A new untouched simulation campaign is still required before publication-grade external validation claims.
