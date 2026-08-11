# Pt-Consistent Tree v1 Validation

## Protocol

- Development rows: 2154
- Locked holdout rows: 546
- Split key: Case + theta1 + theta2 across all panel geometries
- P1 validation: independent curve-only fit with no predicted-Pt tie breaker
- Display fit: predicted P1 slopes are analytically constrained to intersect at direct Pt
- Existing 3-size models are not overwritten.

## Locked Holdout

| Model | Type acc. | Pt MAE | Max force MAE | Curve force RMSE | Raw curve P1 gap | Display P1 gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing 3-Size Tree | 0.9377 | 190.12 | 153.70 | 291.36 | 4519.5708 | N/A |
| Pt-Consistent Tree v1 | 0.9359 | 191.79 | 155.28 | 291.50 | 4788.4700 | 0.0000 |

## Interpretation

The challenger predicts Pt displacement and both normalized P1 slopes together with Pt, max displacement, and max force. The PCA response curve remains a raw model output. Displayed P1 line intercepts are calculated so that both lines intersect at the direct Pt without globally rescaling or reshaping the curve.

The raw curve-only selector is retained as a diagnostic, not as the display fit. Its legacy rule reproduces almost all 6x4 source Pt labels but not most 6x8/8x8 source labels, so forcing that selector onto every geometry would replace the delivered target definition.

Deployment should proceed only when Pt/curve consistency improves without a material regression in Pt MAE, max-force MAE, or curve-force RMSE.
