# DD Laminate AIComp 2026 Research Track

This directory is the tracked control plane for Double-Double laminate model
upgrades inspired by the AIComp 2026 review. It is intentionally separate from
the current production model directories.

## Frozen baseline

The production reference is recorded in
`baselines/dd_3size_pt_consistent_v1.json`. The manifest pins the dataset,
grouped holdout, reports, model artifacts, hashes, and deployment metrics.
Never overwrite files referenced by a frozen baseline manifest.

Verify the baseline before comparison or promotion:

```bash
python scripts/dd_verify_model_baseline.py
```

## New experiment layout

Use one immutable experiment ID per run:

```text
research/dd_aicomp2026/
  configs/<experiment-id>.json
  results/<experiment-id>/
models/dd_laminate_aicomp2026_v1/
  <experiment-id>/
    metadata.json
    artifacts/
reports/dd_aicomp2026_v1/
  <experiment-id>/
```

Recommended experiment IDs use `YYYYMMDD-topic-model-vN`, for example
`20260811-uq-calibration-tree-v1`.

## First upgrade sequence

1. Treat the grouped 546-row partition as a fixed historical benchmark and log
   every use in `holdout_usage_ledger.json`.
2. Split the 2,154-row development set again for calibration fitting.
3. Add calibrated Type probabilities and conformal Pt intervals without
   changing the current production endpoints.
4. Measure coverage, interval width, ECE, Brier score, and abstention behavior.
5. Promote only after a frozen challenger is compared with the baseline on the
   same benchmark; require a new untouched simulation set for publication-grade
   external validation.

The prepared Phase 1 v2 scope is documented in
`docs/DD_UQ_PHASE1_IMMEDIATE_SCOPE.md`. It adds development-only method
selection, panel-geometry-conditioned conformal intervals, and separate
design-space-distance/failure-case reporting without changing production.

See `docs/DD_MODEL_LIFECYCLE.md` and
`docs/reviews/2026-08-11-aicomp-2026-dd-laminate-review.md` for the full policy
and research roadmap.
