# Double-Double Laminate Model Lifecycle

## Purpose

The production models and the AIComp 2026 research track must remain
independently reproducible. Existing artifacts are frozen by hash; challengers
receive new IDs and directories; deployment promotion is an explicit step.

## States

| State | Meaning | May serve production traffic? |
| --- | --- | --- |
| `production_baseline` | Frozen reference currently used for comparison | Yes |
| `challenger` | New experiment under evaluation | No |
| `validated` | Passed the locked holdout and required diagnostics | No |
| `candidate` | Approved for preview or shadow comparison | Preview only |
| `promoted` | Selected replacement with a deployment record | Yes |
| `archived` | Retained for reproducibility, no longer active | No |

## Naming and storage

- Production baseline manifest:
  `research/dd_aicomp2026/baselines/dd_3size_pt_consistent_v1.json`
- New models:
  `models/dd_laminate_aicomp2026_v1/<experiment-id>/artifacts/`
- Experiment configuration:
  `research/dd_aicomp2026/configs/<experiment-id>.json`
- Metrics and plots:
  `reports/dd_aicomp2026_v1/<experiment-id>/`
- Git branch:
  `codex/dd-aicomp2026-uq`

An experiment ID is immutable. A rerun with different code, data, seed, or
hyperparameters receives a new version suffix.

## Baseline protection

1. Do not overwrite any path listed in a frozen manifest.
2. Run `python scripts/dd_verify_model_baseline.py` before and after research
   changes that touch datasets, model loading, or deployment configuration.
3. Record model binaries with Git LFS, while keeping configs, manifests,
   metrics, and reports as regular Git files.
4. Keep the grouped holdout sealed until a challenger configuration is frozen.
5. Report human-reviewed and pseudo-labeled results separately when label
   provenance can affect the conclusion.

## Promotion gate

A challenger can replace the baseline only when all of the following are true:

- It is evaluated on the same 546-row grouped holdout with no Case/angle-group
  leakage.
- Type accuracy, macro-F1, Pt MAE, Max. Force MAE, and curve RMSE are reported.
- Type probability calibration is reported with ECE and Brier score.
- Pt uncertainty is reported with empirical coverage and interval width.
- In-distribution coverage and OOD status are shown separately from statistical
  confidence.
- The P1/Pt display contract and graph behavior pass regression tests.
- A promotion record names the old baseline, new candidate, evidence report,
  Git commit, and rollback path.

## First AIComp upgrade

The first challenger adds uncertainty quantification without changing the
current point predictors:

1. Fit probability calibration using a calibration split taken only from the
   development partition.
2. Fit conformal residual intervals for Pt using the same calibration policy.
3. Preserve the 546-row grouped holdout for final evaluation.
4. Add abstention and OOD behavior only after calibration metrics are stable.

This lets us measure whether reliability information improves before taking on
the larger risk of a new network or inverse-design stack.
