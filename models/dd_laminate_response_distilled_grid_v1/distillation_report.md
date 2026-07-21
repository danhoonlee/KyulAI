# Laminate Forecast Synthetic Grid Distillation v2

Student model distilled from the active Tree + Physics ABD teacher with additional synthetic theta/case grid pseudo-labels.

## Teacher

- `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`

## Student

- Samples: 900
- Synthetic samples: 4107
- Input features: 35
- Sequence length: 128
- Hidden dim: 64
- Branches: 6

## Cross-validation

- Type accuracy: 0.9767 +/- 0.0133
- Macro F1: 0.9775 +/- 0.0139
- Teacher Type agreement: 0.9767
- Pt MAE vs ground truth: 490.16 kips
- Pt MAE vs teacher: 490.16 kips
- Curve normalized RMSE vs ground truth: 0.01073
- Curve normalized RMSE vs teacher: 0.01073

## Interpretation

This model is intended as a compact deployment/student candidate. Synthetic-grid distillation expands the teacher-supervised design space, but the Tree teacher remains the safer high-accuracy reference unless the distilled model is promoted after app/EXE speed tests.
