# Hybrid Max. Force Robust UQ: 20260811-uq-deep-force-robust-v3c

## Protocol

- Point model: frozen Hybrid v3b checkpoint; no retraining.
- Selection evidence: 2,154 development OOF rows only.
- Candidate: maximum supported fold-wise conformal quantile per geometry + Case.
- The reused fixed benchmark was read only after the selection freeze was written.
- Production model, endpoint, and UI were not changed.

## Development OOF selection

| Method | 90% coverage | Mean width (kips) |
| --- | ---: | ---: |
| standard_geometry_case | 89.46% | 2,302.06 |
| fold_robust_geometry_case | 95.13% | 2,972.15 |

Selected: `fold_robust_geometry_case`; mean width ratio `1.2996`.

## Reused fixed benchmark diagnostic

| Level | Coverage | Mean width (kips) |
| --- | ---: | ---: |
| 80% | 87.91% | 2,278.16 |
| 90% | 94.87% | 3,058.64 |
| 95% | 98.35% | 3,996.58 |

This remains engineering evidence from a reused benchmark. A new untouched simulation campaign is required for publication-grade external validation.
