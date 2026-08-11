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

1. Preserve the grouped 546-row holdout as the final comparison gate.
2. Split the 2,154-row development set again for calibration fitting.
3. Add calibrated Type probabilities and conformal Pt intervals without
   changing the current production endpoints.
4. Measure coverage, interval width, ECE, Brier score, and abstention behavior.
5. Promote only after a report compares the challenger against this frozen
   baseline on the same holdout.

See `docs/DD_MODEL_LIFECYCLE.md` and
`docs/reviews/2026-08-11-aicomp-2026-dd-laminate-review.md` for the full policy
and research roadmap.
