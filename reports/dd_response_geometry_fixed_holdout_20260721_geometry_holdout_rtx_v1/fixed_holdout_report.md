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
| Geometry Tree + Physics XAI | 0.9451 | 0.9456 | 247.39 | 0.00293 | 227.99 |
| Geometry GointMLP + Physics XAI | 0.9203 | 0.9247 | 675.61 | 0.01838 | 1035.00 |
| Geometry Hybrid Student | 0.9451 | 0.9444 | 361.05 | 0.00576 | 425.69 |

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.
