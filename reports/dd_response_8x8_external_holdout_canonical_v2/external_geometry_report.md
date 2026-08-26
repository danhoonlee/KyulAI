# DD Laminate 8x8 External Geometry Evaluation

This is the first evaluation on the quarantined 8x8 Case3/Case4 data before those rows are used for training.

- Pt and force-displacement curves are direct targets from the delivered files.
- Type labels are Curve CSV classifier pseudo-labels, so Type scores mean model agreement, not verified ground-truth accuracy.
- No 8x8 Case2 records were delivered; this report covers Case3 and Case4 only.

## Results

| Model | Pseudo-Type agreement | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree canonical v2 | 0.7883 | 3502.40 | 3836.59 | 0.02173 | 3568.82 |
| Geometry GointMLP canonical v2 | 0.7817 | 6788.33 | 15665.36 | 0.02068 | 14299.78 |
| Hybrid Student canonical v2 | 0.7867 | 2106.87 | 5391.55 | 0.01726 | 5146.38 |

## Data Policy

The 8x8 rows remain marked `external_holdout_not_for_training` in this dataset. Promote a reviewed subset into a future training dataset only after preserving a final untouched 8x8 test partition.
