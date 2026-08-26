# Laminate Forecast Synthetic Grid Distillation

Student model distilled from the active Tree + Physics ABD teacher.

## Teacher

- `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`

## Student

- Samples: 1800
- Synthetic samples: 31974
- Input features: 40
- Sequence length: 128
- Hidden dim: 96
- Branches: 10
- Synthetic grid step: 2.5
- Synthetic panel sizes: `6x4,6x8`
- Synthetic base weight: 0.28
- Synthetic confidence power: 1.5
- Synthetic effective weight mean: 0.2551
- Synthetic teacher confidence mean: 0.9349
- Strict CV: True
- Strict synthetic exclusion radius: 2.5
- Fold-local teacher PCA components: 18

## Cross-validation

- Type accuracy: 0.9622 +/- 0.0117
- Macro F1: 0.9601 +/- 0.0143
- Teacher Type agreement: 0.9789
- Pt MAE vs ground truth: 423.02 kips
- Pt MAE vs teacher: 333.96 kips
- Curve normalized RMSE vs ground truth: 0.00951
- Curve normalized RMSE vs teacher: 0.00755

## Interpretation

Strict CV uses fold-local teachers and removes synthetic grid points near validation inputs when enabled. This gives a more conservative performance estimate than the optimistic deployment-style distillation run, where the final teacher is trained on all available data.
