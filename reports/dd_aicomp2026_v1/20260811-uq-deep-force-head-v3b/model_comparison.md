# DD Hybrid v3b Max. Force Head Comparison

## Decision

`20260811-uq-deep-force-head-v3b` is the strongest leakage-controlled neural point-model
challenger so far. A dedicated Max. Force calibration stage improved Max. Force and curve error
without changing Type or Pt predictions. It is not deployed because the reused fixed benchmark's
nominal 90% Max. Force interval covered 87.73%, below the desired 90% level. The Pt-Consistent Tree
remains the deployment leader.

## Protocol

- Development assessment: five grouped OOF folds over 2,154 rows / 718 Case+theta groups.
- Fixed benchmark: 546 rows / 182 groups, opened only after the development gate passed.
- Development-to-benchmark group overlap: 0.
- Max. Force calibration used real fold-fit rows only.
- Teacher targets, synthetic rows, assessment rows, and fixed-benchmark rows were excluded from the
  calibration stage.
- Only the Max. Force row of the final scalar output layer was updated.

## Point Prediction

| Model | Partition | Type accuracy | Pt MAE (kips) | Max. Force MAE (kips) | Mean row curve RMSE (kips) |
| --- | --- | ---: | ---: | ---: | ---: |
| Hybrid v2 | Development OOF | 95.17% | 391.56 | 652.31 | 507.98 |
| Hybrid v3b | Development OOF | 95.17% | 391.56 | 565.56 | 450.33 |
| Hybrid v2 | Fixed benchmark | 93.22% | 411.74 | 660.35 | 492.31 |
| Hybrid v3b | Fixed benchmark | 93.22% | 411.74 | 624.17 | 468.45 |
| Pt-Consistent Tree | Fixed benchmark | 93.59% | 191.79 | 155.28 | 116.77 |

Relative to Hybrid v2, Hybrid v3b improved development OOF Max. Force MAE by 13.30% and mean
curve RMSE by 11.35%. On the fixed benchmark, the corresponding improvements were 5.48% and 4.85%.
Type accuracy and Pt MAE were unchanged on both partitions, confirming that the output-row isolation
worked as intended.

## Statistical Uncertainty

| Model | Fixed 90% Pt coverage | Mean Pt width (kips) | Fixed 90% Max. Force coverage | Mean Max. Force width (kips) |
| --- | ---: | ---: | ---: | ---: |
| Hybrid v2 | 92.12% | 1,484.38 | 91.21% | 2,784.16 |
| Hybrid v3b | 92.12% | 1,484.38 | 87.73% | 2,284.70 |

The Max. Force interval became 17.94% narrower, but fixed-benchmark coverage fell by 3.48 percentage
points. This is useful evidence that better point error does not automatically produce better
calibrated uncertainty. The next iteration should recalibrate or conservatively widen the Max. Force
sidecar using development OOF evidence only, then check the already-reused benchmark as a final
diagnostic.

## Reproducibility Note

The superseded v3a run stopped before reading the fixed benchmark because its development gate failed.
That run exposed a mode-order-dependent random-seed offset: running only Hybrid used a different seed
than the earlier GointMLP-plus-Hybrid experiment. v3b assigns fixed seed offsets by model name, so
optional modes no longer change the Hybrid initialization.

## Evidence

- `metrics.json`: complete OOF, benchmark, calibration, and interval metrics.
- `selection_freeze.json`: fold provenance, row hashes, stage configuration, development gate, and
  frozen UQ decisions.
- `development_gate_hybrid.json`: predeclared gate result with `fixed_benchmark_used=false`.
- `development_oof_predictions_hybrid.csv`: 2,154 OOF predictions plus header.
- `fixed_benchmark_predictions_hybrid.csv`: 546 benchmark predictions plus header.
- Model checkpoint SHA-256: `80dadb85a5a460eb923850538a12e26c0f05834d91d8413bce2e36329fe15bc9`.
