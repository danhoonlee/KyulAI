# DD Laminate Geometry-Aware Fixed Holdout Evaluation

This report evaluates Laminate Forecast models on one deterministic holdout set.

## Split Policy

- Dataset: `data/datasets/DD_cases_2_3_4_geometry_v1`
- Feature set: `theta_physics_geometry_v1`
- Seed: `42`
- Holdout ratio: `0.2`
- Group key: `Case + theta1 + theta2`; no identical case/theta pair appears in both train and holdout.
- Stratification target: `Case + Type`, preserving 6x4/6x8 source coverage as a consequence of the grouped records.

## Split Summary

- Train rows: 1434
- Holdout rows: 366
- Train groups: 239
- Holdout groups: 61

## Results

| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nearest-design lookup (no training) | 0.8470 | 0.8693 | 4988.62 | nan | nan |
| Geometry Tree + Physics XAI | 0.9563 | 0.9534 | 291.69 | 0.00544 | 300.42 |
| Geometry GointMLP + Physics XAI | 0.9317 | 0.9369 | 569.54 | 0.01631 | 868.80 |
| Geometry Hybrid Student | 0.9590 | 0.9585 | 340.35 | 0.00737 | 413.24 |

## Reading this table

`Nearest-design lookup` trains nothing. It answers each held-out row by copying its nearest training row in (theta1, theta2). **A model that does not clearly beat that row has not been shown to generalise** — it is recalling near-duplicates that the split let through. Groups are keyed on the angle pair alone, so all three cases and all panel sizes of one design stay on the same side; keying on case previously put near-identical rows across the split and the lookup beat every trained model on Pt.

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.
