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
| Geometry Tree + Physics XAI | 0.9377 | 0.9347 | 190.12 | 0.00596 | 291.36 |
| Geometry GointMLP + Physics XAI | 0.9212 | 0.9187 | 621.63 | 0.01761 | 994.89 |
| Geometry Hybrid Student | 0.9322 | 0.9291 | 542.87 | 0.00784 | 687.92 |

## Interpretation

Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated model comparisons easier because the test rows do not move between runs.

The deployment default should favor the model with the best Pt and curve metrics unless the product goal is Type-only screening.

## Leave-One-Geometry-Out Transfer

Each fold trains on two panel sizes and evaluates the third panel size inside the development partition. The same Case/theta designs may exist at the two training sizes; this isolates panel-size transfer rather than unseen-design transfer.

| Held-out geometry | Model | Type Acc. | Pt MAE (kips) | Curve Norm RMSE |
| --- | --- | ---: | ---: | ---: |
| 6x4 | Geometry Tree + Physics XAI | 0.8649 | 9828.99 | 0.03110 |
| 6x4 | Geometry GointMLP + Physics XAI | 0.6017 | 10362.35 | 0.04600 |
| 6x4 | Geometry Hybrid Student | 0.4944 | 9950.89 | 0.04406 |
| 6x8 | Geometry Tree + Physics XAI | 0.7897 | 1393.86 | 0.01462 |
| 6x8 | Geometry GointMLP + Physics XAI | 0.8747 | 1009.84 | 0.03002 |
| 6x8 | Geometry Hybrid Student | 0.9457 | 884.15 | 0.02250 |
| 8x8 | Geometry Tree + Physics XAI | 0.7897 | 3643.59 | 0.02210 |
| 8x8 | Geometry GointMLP + Physics XAI | 0.6643 | 7569.93 | 0.03624 |
| 8x8 | Geometry Hybrid Student | 0.6448 | 3821.11 | 0.02007 |
