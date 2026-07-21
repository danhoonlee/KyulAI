# Laminate Forecast Synthetic Grid Distillation

Student model distilled from the active Tree + Physics ABD teacher.

## Teacher

- `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`

## Student

- Samples: 900
- Synthetic samples: 1875
- Input features: 35
- Sequence length: 128
- Hidden dim: 64
- Branches: 6
- Synthetic grid step: 7.5
- Synthetic base weight: 0.28
- Synthetic confidence power: 1.5
- Synthetic effective weight mean: 0.2525
- Synthetic teacher confidence mean: 0.9282
- Strict CV: True
- Strict synthetic exclusion radius: 2.5
- Fold-local teacher PCA components: 18

## Cross-validation

- Type accuracy: 0.9433 +/- 0.0119
- Macro F1: 0.9381 +/- 0.0165
- Teacher Type agreement: 0.9656
- Pt MAE vs ground truth: 671.63 kips
- Pt MAE vs teacher: 532.00 kips
- Curve normalized RMSE vs ground truth: 0.02448
- Curve normalized RMSE vs teacher: 0.02305

## Interpretation

Strict CV uses fold-local teachers and removes synthetic grid points near validation inputs when enabled. This gives a more conservative performance estimate than the optimistic deployment-style distillation run, where the final teacher is trained on all available data.
