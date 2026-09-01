# DD Laminate Geometry-Aware Fixed Holdout Evaluation

This report evaluates Laminate Forecast models on one deterministic holdout set.

## Split Policy

- Dataset: `data/datasets/DD_cases_2_3_4_geometry_3size_v1`
- Feature set: `theta_physics_geometry_canonical_v2`
- Seed: `42`
- Holdout ratio: `0.2`
- Group key: `Case + theta1 + theta2`; no identical case/theta pair appears in both train and holdout.
- Stratification target: `Case + Type`, preserving 6x4/6x8 source coverage as a consequence of the grouped records.

## Split Summary

- Train rows: 2151
- Holdout rows: 549
- Train groups: 239
- Holdout groups: 61

## Results

| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nearest-design lookup (no training) | 0.7741 | 0.7743 | 6879.06 | nan | nan |
| Geometry Tree + Physics XAI | 0.9581 | 0.9561 | 204.08 | 0.00652 | 670.14 |
| Geometry GointMLP + Physics XAI | 0.9581 | 0.9561 | 675.29 | 0.01417 | 1052.19 |
| Geometry Hybrid Student | 0.9563 | 0.9534 | 327.87 | 0.00755 | 708.99 |

### Geometry Tree + Physics XAI by panel

Pt MAE is an absolute error, and Pt itself differs by more than a factor of two across panels, so the relative column is the one to compare.

| Panel | n | Type Acc. | Pt MAE | Pt mean | Pt MAE / Pt mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6x4 | 183 | 0.9454 | 265.15 | 16,560 | 1.60% |
| 6x8 | 183 | 0.9727 | 153.59 | 7,389 | 2.08% |
| 8x8 | 183 | 0.9563 | 193.51 | 5,472 | 3.54% |

## Reading this table

`Nearest-design lookup` trains nothing. It answers each held-out row by copying its nearest training row in (theta1, theta2). **A model that does not clearly beat that row has not been shown to generalise** — it is recalling near-duplicates that the split let through. Groups are keyed on the angle pair alone, so all three cases and all panel sizes of one design stay on the same side; keying on case previously put near-identical rows across the split and the lookup beat every trained model on Pt.

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.
