# DD 3-Size Tree UQ Calibration v1

## Protocol

- Fit: 1725 rows / 575 groups
- Calibration: 429 rows / 143 groups
- Locked Holdout: 546 rows / 182 groups
- Group key: Case + theta1 + theta2; overlap across all partitions: 0
- The locked Holdout was used only for final evaluation.

## Type probability calibration

- Temperature: 1.191258
- Selected method: identity
- Decision: Temperature scaling failed the calibration-only NLL/Brier/ECE guard; raw probabilities are retained.

| Holdout metric | Raw | Calibrated |
| --- | ---: | ---: |
| Accuracy | 0.9176 | 0.9176 |
| NLL | 0.18980 | 0.19478 |
| Brier score | 0.11424 | 0.11593 |
| ECE | 0.01225 | 0.02763 |

## Point prediction quality

- Type accuracy: 0.9176
- Type macro-F1: 0.9133
- Pt MAE: 236.01 kips
- Max. Force MAE: 218.94 kips
- Curve force RMSE: 417.09 kips

## Split-conformal intervals on locked Holdout

| Target | Nominal | Empirical | Mean width | Quantile |
| --- | ---: | ---: | ---: | ---: |
| Pt | 80% | 0.8168 | 467.38 | 233.69 |
| Pt | 90% | 0.9103 | 901.33 | 450.66 |
| Pt | 95% | 0.9670 | 1619.53 | 809.77 |
| Max. Force | 80% | 0.8370 | 677.54 | 338.77 |
| Max. Force | 90% | 0.9487 | 1660.51 | 830.25 |
| Max. Force | 95% | 0.9853 | 2780.14 | 1390.07 |

## Interpretation

- This is a strict split-calibration experiment, so the point model is trained on fewer rows than the production baseline.
- Calibration is considered useful only when NLL/Brier/ECE improve without changing Type accuracy.
- Interval quality must be judged by empirical coverage and width together; wider intervals alone are not an improvement.
- Geometry and Case subgroup results are retained in `metrics.json` for failure analysis.
