# DD Laminate UQ Phase 1 Immediate Scope

## Objective

Complete the AIComp 2026 immediate uncertainty work without changing the
deployed Tree, GointMLP, or Hybrid predictors. The output of this phase is an
offline, reproducible evidence package. It is not a production rollout.

## Current state

- The immutable production reference is
  `dd-3size-pt-consistent-v1-20260811`.
- Tree UQ v1 measured probability calibration and pooled split-conformal
  intervals.
- Raw Tree Type probabilities passed the calibration-only selection guard;
  temperature scaling was rejected.
- Pooled Pt intervals met overall nominal coverage but under-covered the 6x4
  subgroup at 80% and 90%.
- The 546-row grouped test partition has now been used as a fixed benchmark in
  several comparisons. It is no longer described as a pristine external test
  set for publication claims.

## Prepared next experiment

Experiment ID: `20260811-uq-mondrian-ood-tree-v2`

### 1. Development-only interval selection

Use grouped out-of-fold predictions inside the 2,154-row development
partition. Compare:

- pooled absolute-residual conformal intervals;
- panel-geometry-conditioned Mondrian intervals for 6x4, 6x8, and 8x8;
- pooled fallback behavior for any unsupported geometry.

The method is selected from development-only results. The fixed benchmark may
be reported after the choice is frozen, but it cannot change that choice.

### 2. Separate reliability signals

Report these fields independently:

- `type_probability`: classifier probability after the accepted calibration
  policy;
- `prediction_interval`: Pt and Max. Force 80%, 90%, and 95% intervals;
- `design_space_distance`: standardized nearest-neighbour distance in the
  model's canonical input-feature space;
- `interval_fallback`: whether a pooled interval was used because the geometry
  was unsupported or sparse;
- `model_status`: research challenger, fixed benchmark result, or promoted.

No single combined reliability percentage is introduced in this phase.

### 3. Failure-case report

For Type, Pt, Max. Force, and curve error, report:

- Case, Type, and panel-size subgroup metrics;
- the largest-error rows with Case, theta1, theta2, geometry, target,
  prediction, interval, and design-space distance;
- error by design-space-distance bin;
- Spearman correlation between distance and absolute error;
- interval misses and pooled-fallback rows.

## Acceptance criteria

- Case + theta1 + theta2 groups never cross fit, calibration, or assessment
  partitions.
- Every model/configuration choice is made inside development data.
- Geometry-conditioned intervals are retained only if they reduce subgroup
  coverage error without unacceptable interval inflation.
- Nominal 90% coverage is reported overall and by geometry/Case.
- OOD distance is described as a model-input coverage indicator, not a proof
  of physical invalidity.
- Fixed-benchmark usage is appended to the usage ledger before every run.
- Production API/UI remains unchanged until an explicit promotion record is
  approved.

## Execution order

1. Run the Phase 1 preflight check.
2. Generate grouped out-of-fold development predictions.
3. Freeze the pooled-versus-Mondrian selection rule.
4. Fit final calibration objects on development-only residuals.
5. Run the fixed benchmark once for the frozen v2 configuration.
6. Review subgroup and failure-case evidence.
7. Decide whether to keep as challenger, expose in preview, or archive.

## External validation requirement

A new untouched simulation campaign is required before publication-grade
generalization or calibrated-coverage claims. The current 546-row partition is
valuable as a stable regression benchmark, but repeated historical use means
it is not independent external validation.
