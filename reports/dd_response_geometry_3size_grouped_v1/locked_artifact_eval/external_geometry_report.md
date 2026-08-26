# DD Laminate Locked Holdout Evaluation

This report evaluates deployment artifacts on the locked Case/theta groups that were excluded from real training and synthetic distillation.

- Pt and force-displacement curves are direct targets from the delivered files.
- 6x4 Type labels are curated; 6x8 and 8x8 Type labels include Curve CSV classifier pseudo-labels.
- Cases: `{'Case2': 183, 'Case3': 183, 'Case4': 180}`
- Panel sizes: `{'6x4': 182, '6x8': 182, '8x8': 182}`

## Results

### Raw surrogate outputs

| Model | Pseudo-Type agreement | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree + Physics XAI | 0.9377 | 190.12 | 153.70 | 0.00596 | 291.36 |
| Geometry GointMLP + Physics XAI | 0.9048 | 532.84 | 1011.54 | 0.01549 | 1017.90 |
| Geometry Hybrid Student | 0.9341 | 305.64 | 389.45 | 0.00649 | 438.50 |

### Serving-consistent outputs

The web/app response applies monotonic smoothing and Pt-curve consistency after inference. That step preserves predicted Pt but can rescale max force so the fitted kink matches Pt.

| Model | Pseudo-Type agreement | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree + Physics XAI | 0.9377 | 190.12 | 7838.84 | 0.00596 | 10858.31 |
| Geometry GointMLP + Physics XAI | 0.9048 | 532.84 | 9722.35 | 0.01531 | 13182.87 |
| Geometry Hybrid Student | 0.9341 | 305.64 | 7789.35 | 0.00653 | 11540.48 |

## Data Policy

These rows remain locked and must not be used for fitting, normalization, hyperparameter selection, or synthetic teacher labels. Type metrics on pseudo-labeled rows are agreement metrics; Pt and curve metrics are direct-target metrics.
