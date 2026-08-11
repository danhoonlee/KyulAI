# DD Laminate Model Catalog

Updated: 2026-07-23

## Decision Summary

- Best raw numerical model on the common 546-row, three-size locked Holdout:
  `response_geometry_tree_3size_grouped_v1`.
- Best operational model when prediction accuracy and graph/Pt consistency are considered together:
  `response_pt_consistent_tree_3size_grouped_v1`.
- Best neural model:
  `response_pt_consistent_hybrid_3size_grouped_v1`.
- Best standalone deep-learning model without a Tree teacher at inference:
  `response_pt_consistent_goint_3size_grouped_v1`.
- Pt-consistency is an output contract, not an automatic accuracy improvement. It guarantees that
  the two displayed P1 lines intersect at Predicted Pt without rescaling the raw response curve.

## Directly Comparable Three-Size Models

All models below use the same 2,154-row development split and the same untouched 546-row locked
Holdout, grouped by Case + theta1 + theta2 across 6x4, 6x8, and 8x8 panels.

| Family | Model | Type accuracy | Pt MAE (kips) | Max. Force MAE (kips) | Curve Force RMSE (kips) | Display P1/Pt gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Tree | Original 3-Size Tree | **0.9377** | **190.12** | **153.70** | **291.36** | Not guaranteed |
| Tree | Pt-Consistent Tree v1 | 0.9359 | 191.79 | 155.28 | 291.50 | **0.00** |
| Standalone DL | Original 3-Size GointMLP | 0.9048 | 532.84 | 1011.54 | 1017.90 | Not guaranteed |
| Standalone DL | Pt-Consistent GointMLP v1 | **0.9139** | **525.37** | **867.40** | **908.29** | **0.00** |
| Hybrid DL | Original 3-Size Hybrid | **0.9341** | 305.64 | 389.45 | 438.50 | Not guaranteed |
| Hybrid DL | Pt-Consistent Hybrid v1 | 0.9322 | **286.66** | **362.38** | **425.62** | **0.00** |

## Interpretation

### Tree

The original three-size Tree is still the strict numerical winner. The Pt-Consistent Tree is only
slightly worse: Type accuracy differs by 0.18 percentage points and Pt MAE by 1.67 kips. That small
cost buys an exact, non-misleading displayed P1/Pt intersection. Therefore the Pt-Consistent Tree
is the preferred product-facing candidate even though it is not literally the lowest-error Tree.

### Standalone Deep Learning

The Pt-Consistent GointMLP is a genuine improvement over its matching original GointMLP on every
main Holdout metric. It remains substantially weaker than both Tree models, especially for 6x4 and
Type 3 curves. Keep it as the standalone-DL research baseline, not the default predictor.

### Hybrid Deep Learning

The Pt-Consistent Hybrid improves Pt, Max. Force, and curve regression over the original Hybrid,
while Type accuracy is 0.18 percentage points lower. It is the strongest current neural candidate
and should be the base for Pt-Consistent Residual Hybrid v2.

## Current Deployment State

The production Laminate registry currently exposes these older `canonical_v2` models:

- `response_geometry_tree_canonical_v2`
- `response_geometry_goint_canonical_v2`
- `response_hybrid_student_canonical_v2`

They were evaluated on a different 6x4 + 6x8, 1,800-row dataset and a 364-row Holdout. Their
scores must not be placed in the same ranking table as the newer three-size models.

The isolated research preview at `https://laminate.imperialax.com/preview/3size` exposes the six
directly comparable original/Pt-consistent pairs from the table above. No production replacement
has been made yet.

## Recommended Active Set

Keep only these models visible in future product-facing selectors:

1. `Pt-Consistent Tree` - recommended default and best overall operational model.
2. `Pt-Consistent Hybrid` - recommended neural/teacher-student comparison model.
3. `Pt-Consistent GointMLP` - optional standalone deep-learning research model.

Keep the three original three-size models as hidden benchmark artifacts. Move older theta-only,
CSV classifier, pre-geometry response, early distillation, challenger, and superseded XAI model
directories to a documented archive rather than deleting them until reproducibility hashes and
dependencies are recorded.

## XAI Naming Rule

XAI should not be counted as a separate predictive model when it is only an explanation layer over
an existing checkpoint. Name product options by prediction family (`Tree`, `GointMLP`, `Hybrid`)
and show XAI as a capability. Only treat it as a separate model when the actual training feature
set or checkpoint differs.

## Next Model

`Pt-Consistent Residual Hybrid v2` should use the Pt-Consistent Tree as the base predictor and train
a physics-structured neural residual corrector using out-of-fold Tree predictions. The current
546-row Holdout must remain locked for the final comparison.
