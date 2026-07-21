# Laminate Forecast Distillation v1

Student model distilled from the active Tree + Physics ABD teacher.

## Teacher

- `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`

## Student

- Samples: 900
- Input features: 35
- Sequence length: 128
- Hidden dim: 64
- Branches: 6

## Cross-validation

- Type accuracy: 0.9378 +/- 0.0119
- Macro F1: 0.9352 +/- 0.0156
- Teacher Type agreement: 0.9378
- Pt MAE vs ground truth: 739.90 kips
- Pt MAE vs teacher: 739.90 kips
- Curve normalized RMSE vs ground truth: 0.01864
- Curve normalized RMSE vs teacher: 0.01864

## Interpretation

This model is intended as a compact deployment/student candidate. The Tree teacher remains the safer high-accuracy reference unless the distilled model is promoted after app/EXE speed tests.
