# DD Tree UQ v2: Grouped OOF, Mondrian, and OOD Diagnostics

## Protocol

- Development OOF: 2154 rows / 718 Case+theta groups
- Folds: 5
- Fixed benchmark: 546 rows / 182 groups
- Interval method selection used development OOF evidence only.
- The benchmark was evaluated only after `selection_freeze.json` was written.
- Production model and endpoints were not changed.

## Development OOF point quality

- Type accuracy: 0.9475
- Type macro-F1: 0.9441
- Pt MAE: 177.03 kips
- Max. Force MAE: 214.00 kips
- Mean per-row curve RMSE: 161.12 kips

## Development-only interval selection

| Target | Selected | Pooled mean gap | Mondrian mean gap | Width ratio |
| --- | --- | ---: | ---: | ---: |
| pt | mondrian | 0.0909 | 0.0033 | 0.9380 |
| max_force | mondrian | 0.0160 | 0.0019 | 1.0179 |

## Fixed-benchmark interval coverage

| Target | Method | Nominal | Empirical | Mean width |
| --- | --- | ---: | ---: | ---: |
| pt | mondrian | 80% | 0.8388 | 482.49 |
| pt | mondrian | 90% | 0.9176 | 695.52 |
| pt | mondrian | 95% | 0.9670 | 1044.95 |
| max_force | mondrian | 80% | 0.8498 | 549.03 |
| max_force | mondrian | 90% | 0.9286 | 919.93 |
| max_force | mondrian | 95% | 0.9725 | 1409.63 |

## Critical subgroup coverage

| Target | Nominal | Case 2 | Case 3 | Case 4 |
| --- | ---: | ---: | ---: | ---: |
| pt | 80% | 0.9180 | 0.6776 | 0.9222 |
| pt | 90% | 0.9563 | 0.8361 | 0.9611 |
| pt | 95% | 0.9672 | 0.9508 | 0.9833 |
| max_force | 80% | 0.9672 | 0.6230 | 0.9611 |
| max_force | 90% | 0.9781 | 0.8251 | 0.9833 |
| max_force | 95% | 0.9836 | 0.9508 | 0.9833 |

## OOD and failure-case signal

| Partition | Target | Spearman rho: distance vs. error |
| --- | --- | ---: |
| development_oof | pt | 0.0192 |
| development_oof | max_force | -0.0054 |
| development_oof | curve_force_rmse | -0.0052 |
| development_oof | type_error | 0.0671 |
| fixed_benchmark | pt | -0.0566 |
| fixed_benchmark | max_force | -0.1581 |
| fixed_benchmark | curve_force_rmse | -0.1405 |
| fixed_benchmark | type_error | 0.0434 |

## Interpretation

The selected intervals are a statistical sidecar for the frozen Pt-Consistent Tree. Type probability, interval width, and design-space distance remain separate signals. Distance is a model-input coverage indicator, not proof that a laminate is physically invalid.

The simple kNN distance did not track Pt, Max. Force, or curve error consistently. It must not be presented as an error-confidence score. The geometry-conditioned intervals also under-cover Case 3 at the 80% and 90% levels, so this run remains a challenger. The next interval candidate should condition on both panel geometry and Case, with a pooled fallback for sparse groups.

The 546-row partition is a reused fixed benchmark. A new untouched simulation set is required before publication-grade external-validation claims.
