# DD Laminate UQ Model Comparison

## Protocol

- Dataset: 2,700 rows across 6x4, 6x8, and 8x8 panels.
- Development: 2,154 rows / 718 unique Case + theta1 + theta2 groups.
- Fixed benchmark: 546 rows / 182 groups, with zero design-group overlap.
- Assessment: five-fold GroupKFold on development data, followed by one frozen fixed-benchmark read.
- Interval selection: development OOF predictions only. The fixed benchmark did not select models,
  calibration, interval conditioning, or hyperparameters.
- Curve metric: mean of each sample's 128-point force RMSE. This definition is shared by all three
  model families in the table below.

## Fixed-Benchmark Point Performance

| Model | Type accuracy | Pt MAE (kips) | Max. Force MAE (kips) | Mean row Curve RMSE (kips) |
| --- | ---: | ---: | ---: | ---: |
| Pt-Consistent Tree | **0.9359** | **191.79** | **155.28** | **116.77** |
| Pt-Consistent GointMLP | 0.9176 | 876.01 | 1,361.00 | 1,065.80 |
| Pt-Consistent Hybrid | 0.9304 | 499.66 | 659.06 | 540.14 |

## Fixed-Benchmark 90% Intervals

All models selected panel geometry + Case conditioning using development OOF evidence only.

| Model | Pt coverage | Pt mean width (kips) | Max. Force coverage | Max. Force mean width (kips) |
| --- | ---: | ---: | ---: | ---: |
| Pt-Consistent Tree | **93.96%** | **686.43** | **96.70%** | **887.67** |
| Pt-Consistent GointMLP | 93.59% | 3,252.75 | 89.93% | 5,386.60 |
| Pt-Consistent Hybrid | 89.19% | 1,593.42 | 89.56% | 2,582.67 |

## Probability Calibration

- GointMLP selected temperature scaling with frozen temperature 1.3173. Development OOF expected
  calibration error improved from 1.83% to 1.32%.
- Hybrid selected temperature scaling with frozen temperature 2.1406. Development OOF expected
  calibration error improved from 2.76% to 0.76%.
- Hybrid 80% intervals under-covered on the fixed benchmark: Pt 73.26% and Max. Force 76.92%.
  This is a deployment blocker even though its point prediction is materially better than GointMLP.

## Decision

- Keep the Pt-Consistent Tree as the deployment leader. It has the best point accuracy and the
  narrowest intervals on the shared fixed benchmark.
- Preserve the Pt-Consistent Hybrid as the primary Deep Learning challenger. It clearly improves on
  standalone GointMLP, but it is not ready to replace Tree.
- Do not promote the standalone GointMLP challenger.
- Do not change the production model registry, endpoints, or UI from this experiment.
- Build Deep Learning v2 with fold-local response pretraining followed by Pt-consistent fine-tuning.
  The same frozen split and OOF-only selection rules must be retained, and the fixed benchmark must
  remain unavailable during tuning.

## Evidence Boundary

The 546-row fixed benchmark has been reused by earlier project experiments. It is suitable for the
current internal comparison, but it is not a pristine external validation set. Publication-grade
claims still require a newly generated untouched simulation set collected after the final protocol is
frozen.
