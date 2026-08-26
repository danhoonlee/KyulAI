# DD Laminate Geometry-Aware Fixed Holdout Evaluation

This report evaluates Laminate Forecast models on one deterministic holdout set.

## Split Policy

- Dataset: `data/datasets/DD_cases_2_3_4_geometry_3size_v1`
- Feature set: `theta_physics_geometry_v1`
- Seed: `42`
- Holdout ratio: `0.2`
- Split source: `data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv`
- Group key: `Case + theta1 + theta2`; no identical case/theta pair appears in both train and holdout.
- The same group assignment is applied to every panel geometry.

## Split Summary

- Train rows: 2154
- Holdout rows: 546
- Train groups: 718
- Holdout groups: 182

## Results

| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree + Physics XAI | 0.9322 | 0.9288 | 191.28 | 0.00599 | 287.84 |

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.

## Leave-One-Geometry-Out Transfer

Each fold trains on two panel sizes and evaluates the third panel size inside the development partition.

| Held-out geometry | Model | Type Acc. | Pt MAE (kips) | Curve Norm RMSE |
| --- | --- | ---: | ---: | ---: |
| 6x4 | Geometry Tree + Physics XAI | 0.8649 | 9829.67 | 0.03119 |
| 6x8 | Geometry Tree + Physics XAI | 0.7897 | 1530.87 | 0.01460 |
| 8x8 | Geometry Tree + Physics XAI | 0.7897 | 3522.68 | 0.02225 |
