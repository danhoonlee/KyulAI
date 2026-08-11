# Hybrid Max. Force UQ Comparison

## Scope

- Point model: the frozen Hybrid v3b checkpoint.
- Changed component: Max. Force conformal interval sidecar only.
- Selection evidence: 2,154 grouped development OOF rows across five folds.
- Reporting evidence: the reused 546-row fixed benchmark, opened only after the v3c selection freeze.
- Unchanged outputs: Type probabilities, Pt prediction, Max. Force point prediction, predicted curve, and Pt intervals.

## Fixed-benchmark comparison at 90% nominal coverage

| Candidate | Max. Force coverage | Mean interval width (kips) | Interpretation |
| --- | ---: | ---: | --- |
| Hybrid v3b standard geometry + Case | 87.73% | 2,284.70 | Narrowest, but under-covers overall. |
| Hybrid v2 standard geometry + Case | 91.21% | 2,784.16 | Meets nominal coverage with moderate width. |
| Hybrid v3c fold-robust geometry + Case | 94.87% | 3,058.64 | Strongest overall coverage, but conservative. |

Relative to v3b, v3c increases fixed-benchmark coverage by 7.14 percentage points and increases
mean interval width by 33.87%. Relative to v2, coverage increases by 3.66 percentage points and
mean interval width increases by 9.86%.

## v3c fixed-benchmark coverage

| Nominal level | Empirical coverage | Mean width (kips) |
| --- | ---: | ---: |
| 80% | 87.91% | 2,278.16 |
| 90% | 94.87% | 3,058.64 |
| 95% | 98.35% | 3,996.58 |

At the 90% level, `6x8 | Case2` remains the only geometry-plus-Case subgroup below nominal coverage:
86.89% with a 2,367.72-kip mean interval width. Every other geometry-plus-Case subgroup reaches at
least 91.67% coverage.

## Decision

The v3c sidecar is retained as a research challenger because it restores overall Max. Force coverage
without retraining or changing the point model. It is not approved for production deployment:

1. The fixed benchmark has already been reused for prior model comparisons.
2. The interval is materially wider than v3b and v2.
3. The `6x8 | Case2` subgroup still under-covers at the 90% target.

The Pt-Consistent Tree remains the deployment leader. Publication-grade validation requires a new,
untouched simulation campaign after the model and interval method are frozen.
