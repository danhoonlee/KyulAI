# DD Tree UQ v3: Geometry + Case Conformal Intervals

## Protocol

- Development OOF source: 2154 rows / 5 grouped folds
- Fixed benchmark: 546 rows
- Geometry versus geometry+Case selection used development OOF evidence only.
- The fixed benchmark was read only after `selection_freeze.json` was written.
- The point predictor, production API, and production UI were not changed.

## Development-only selection

| Target | Geometry gap | Geometry+Case gap | Width ratio | Selected |
| --- | ---: | ---: | ---: | --- |
| pt | 0.0709 | 0.0036 | 0.9844 | geometry_case |
| max_force | 0.0867 | 0.0055 | 0.9585 | geometry_case |

## Fixed-benchmark selected interval coverage

| Target | Nominal | Empirical | Mean width | Fallback |
| --- | ---: | ---: | ---: | ---: |
| pt | 80% | 0.8608 | 469.80 | 0.0000 |
| pt | 90% | 0.9396 | 686.43 | 0.0000 |
| pt | 95% | 0.9634 | 968.03 | 0.0000 |
| max_force | 80% | 0.8864 | 554.91 | 0.0000 |
| max_force | 90% | 0.9670 | 887.67 | 0.0000 |
| max_force | 95% | 0.9872 | 1269.94 | 0.0000 |

## Fixed-benchmark diagnostic comparison

| Target | Geometry gap | Geometry+Case gap | Geometry width | Geometry+Case width |
| --- | ---: | ---: | ---: | ---: |
| pt | 0.0674 | 0.0436 | 740.99 | 708.09 |
| max_force | 0.0935 | 0.0636 | 959.53 | 904.18 |

## Fixed-benchmark Case coverage

| Target | Nominal | Case 2 | Case 3 | Case 4 |
| --- | ---: | ---: | ---: | ---: |
| pt | 80% | 0.8634 | 0.8361 | 0.8833 |
| pt | 90% | 0.9290 | 0.9508 | 0.9389 |
| pt | 95% | 0.9454 | 0.9727 | 0.9722 |
| max_force | 80% | 0.9180 | 0.8415 | 0.9000 |
| max_force | 90% | 0.9672 | 0.9727 | 0.9611 |
| max_force | 95% | 0.9836 | 0.9945 | 0.9833 |

## Interpretation

The geometry+Case candidate was selected before benchmark evaluation. It corrects the systematic Case imbalance left by geometry-only intervals while retaining a pooled fallback for unseen or insufficiently supported groups.

This sidecar remains a challenger until its API/UI contract is reviewed. The 546-row partition is a reused fixed benchmark, so a new untouched simulation set is still required for publication-grade external-validation claims.
