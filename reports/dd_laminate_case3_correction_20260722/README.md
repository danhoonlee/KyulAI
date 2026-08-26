# Case 3 Physics Feature Correction Baseline

## Confirmed definition

- Case 3: `[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂`
- Canonical feature set: `theta_physics_geometry_canonical_v2`
- Historical compatibility feature set: `theta_physics_geometry_v1`

The raw force-displacement curves, Type labels, and Pt targets remain valid when
the simulations used the confirmed Case 3 layup. Only CLT/ABD-derived features
from the historical Case 3 expansion need correction and model retraining.

## Historical strict grouped CV baseline

| Model | Type accuracy | Macro F1 | Pt MAE (kips) | Curve norm RMSE | Curve force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree | 0.9561 | 0.9511 | 313.91 | 0.00571 | 401.38 |
| Geometry GointMLP | 0.9511 | 0.9480 | 738.04 | 0.02698 | 1241.92 |
| Hybrid Student | 0.9622 | 0.9601 | 423.02 | 0.00951 | 648.20 |

## Historical fixed holdout baseline

| Model | Type accuracy | Pt MAE (kips) | Curve norm RMSE |
| --- | ---: | ---: | ---: |
| Geometry Tree | 0.9451 | 247.39 | 0.00293 |
| Geometry GointMLP | 0.9203 | 675.61 | 0.01838 |
| Hybrid Student | 0.9451 | 361.05 | 0.00576 |

These values are comparison baselines only. They were produced with the
historical Case 3 physics-feature expansion and must not be reported as metrics
for the corrected canonical feature set.

## Corrected canonical results

### Five-fold grouped CV

| Model | Type accuracy | Macro F1 | Pt MAE (kips) | Curve norm RMSE | Curve force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree | 0.9639 | 0.9634 | 267.79 | 0.00570 | 382.42 |
| Geometry GointMLP | 0.9567 | 0.9567 | 706.01 | 0.03069 | 1207.70 |
| Hybrid Student | 0.9728 | 0.9720 | 393.28 | 0.00777 | 569.12 |

### Deterministic grouped holdout

| Model | Type accuracy | Macro F1 | Pt MAE (kips) | Curve norm RMSE | Curve force RMSE (kips) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Geometry Tree | 0.9451 | 0.9466 | 200.21 | 0.00449 | 400.68 |
| Geometry GointMLP | 0.9258 | 0.9318 | 717.14 | 0.02174 | 1110.08 |
| Hybrid Student | 0.9451 | 0.9467 | 303.19 | 0.00588 | 493.08 |

The corrected Geometry Tree remains the deployment default because it has the
best Pt and response-curve errors. The corrected Hybrid Student remains the
Type-screening challenger because it has the highest grouped-CV classification
accuracy. GointMLP remains available as the direct deep-learning comparison.

## Promotion gate

The corrected artifacts can replace deployment defaults only after:

1. canonical sequence regression tests pass;
2. five-fold grouped CV completes for Tree, GointMLP, and Hybrid Student;
3. the deterministic grouped holdout completes;
4. model metadata records `theta_physics_geometry_canonical_v2`;
5. API and frontend smoke tests confirm the same canonical artifact is served.

All five gates passed on 2026-07-22. The API, web UI, iOS app, and Android app
now default to the `canonical_v2` model keys while historical artifacts remain
registered for compatibility with saved prediction records.
