# Laminate Forecast Synthetic Grid Distillation

Student model distilled from the active Tree + Physics ABD teacher with confidence-weighted synthetic theta/case grid pseudo-labels.

## Teacher

- `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`

## Student

- Samples: 900
- Synthetic samples: 7203
- Input features: 35
- Sequence length: 128
- Hidden dim: 80
- Branches: 8
- Synthetic grid step: 3.75
- Synthetic base weight: 0.3
- Synthetic confidence power: 1.5
- Synthetic effective weight mean: 0.2702
- Synthetic teacher confidence mean: 0.9273

## Cross-validation

- Type accuracy: 0.9789 +/- 0.0124
- Macro F1: 0.9784 +/- 0.0150
- Teacher Type agreement: 0.9789
- Pt MAE vs ground truth: 469.74 kips
- Pt MAE vs teacher: 469.74 kips
- Curve normalized RMSE vs ground truth: 0.00977
- Curve normalized RMSE vs teacher: 0.00977

## Interpretation

This model is intended as a compact deployment/student candidate. Synthetic-grid distillation expands the teacher-supervised design space, but the Tree teacher remains the safer high-accuracy reference unless the distilled model is promoted after app/EXE speed tests.
