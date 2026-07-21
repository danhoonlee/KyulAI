# Laminate Forecast Synthetic Grid Distillation

Student model distilled from the active Tree + Physics ABD teacher.

## Teacher

- `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`

## Student

- Samples: 900
- Synthetic samples: 15987
- Input features: 35
- Sequence length: 128
- Hidden dim: 96
- Branches: 10
- Synthetic grid step: 2.5
- Synthetic base weight: 0.28
- Synthetic confidence power: 1.5
- Synthetic effective weight mean: 0.2522
- Synthetic teacher confidence mean: 0.9274
- Strict CV: True
- Strict synthetic exclusion radius: 2.5
- Fold-local teacher PCA components: 18

## Cross-validation

- Type accuracy: 0.9556 +/- 0.0161
- Macro F1: 0.9513 +/- 0.0173
- Teacher Type agreement: 0.9689
- Pt MAE vs ground truth: 501.14 kips
- Pt MAE vs teacher: 347.39 kips
- Curve normalized RMSE vs ground truth: 0.01271
- Curve normalized RMSE vs teacher: 0.01065

## Interpretation

Strict CV uses fold-local teachers and removes synthetic grid points near validation inputs when enabled. This gives a more conservative performance estimate than the optimistic deployment-style distillation run, where the final teacher is trained on all available data.
