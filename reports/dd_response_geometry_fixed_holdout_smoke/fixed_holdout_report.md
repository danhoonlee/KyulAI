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

- Train rows: 1436
- Holdout rows: 364
- Train groups: 718
- Holdout groups: 182

## Results

| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree + Physics XAI | 0.9423 | 0.9419 | 248.48 | 0.00288 | 228.42 |

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.
