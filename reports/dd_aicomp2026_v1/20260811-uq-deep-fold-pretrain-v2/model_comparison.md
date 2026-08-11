# DD Laminate Deep Learning v2 Comparison

## Protocol

- Dataset: 2,700 rows across 6x4, 6x8, and 8x8 panels.
- Development: 2,154 rows / 718 unique Case + theta1 + theta2 groups.
- Fixed benchmark: 546 rows / 182 groups, with zero design-group overlap.
- Assessment: five-fold GroupKFold on development data, followed by one frozen fixed-benchmark read.
- Pretraining: response Type, ordinal Type, response scalars, and the 128-point curve using only each
  fold's fit rows. P1, teacher targets, synthetic rows, fold assessment rows, and fixed-benchmark rows
  were excluded from pretraining.
- Fine-tuning: the existing Pt-consistent objective. Hybrid fine-tuning additionally used a fold-local
  Tree teacher and synthetic rows that excluded assessment and benchmark design groups.
- Interval and temperature selection used development OOF predictions only.
- Production models, endpoints, and UI were not changed.

## Fixed-Benchmark Point Performance

| Model | Type accuracy | Pt MAE (kips) | Max. Force MAE (kips) | Mean row Curve RMSE (kips) |
| --- | ---: | ---: | ---: | ---: |
| Pt-Consistent Tree | **0.9359** | **191.79** | **155.28** | **116.77** |
| GointMLP v1 | 0.9176 | 876.01 | 1,361.00 | 1,065.80 |
| GointMLP v2 fold-pretrained | 0.9194 | 766.17 | 1,077.71 | 852.75 |
| Hybrid v1 | 0.9304 | 499.66 | **659.06** | 540.14 |
| Hybrid v2 fold-pretrained | **0.9322** | **411.74** | 660.35 | **492.31** |

Relative to v1, fold-local pretraining reduced GointMLP Pt MAE by 12.5%, Max. Force MAE by 20.8%,
and curve RMSE by 20.0%. Hybrid Pt MAE fell by 17.6% and curve RMSE by 8.9%; Hybrid Max. Force MAE
was effectively unchanged, increasing by 1.29 kips (0.2%). Both v2 models gained 0.18 percentage
points of Type accuracy on the fixed benchmark.

## Fixed-Benchmark 90% Intervals

| Model | Pt conditioning | Pt coverage | Pt mean width | Max. Force conditioning | Max. Force coverage | Max. Force mean width |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| GointMLP v1 | geometry + Case | 93.59% | 3,252.75 | geometry + Case | 89.93% | 5,386.60 |
| GointMLP v2 | geometry + Case | 93.41% | 3,049.98 | geometry | 92.31% | 4,680.56 |
| Hybrid v1 | geometry + Case | 89.19% | 1,593.42 | geometry + Case | 89.56% | 2,582.67 |
| Hybrid v2 | geometry + Case | 92.12% | 1,484.38 | geometry + Case | 91.21% | 2,784.16 |

- GointMLP v2 selected geometry-only Max. Force intervals because that choice passed the frozen
  development-only coverage and width guards.
- Hybrid v2 corrected the v1 90% under-coverage for both Pt and Max. Force. Its Max. Force interval
  became wider, matching the unchanged point error rather than implying unsupported precision.
- Temperature scaling was retained for both v2 models. Development OOF ECE was 0.73% for GointMLP
  and 0.92% for Hybrid after cross-fitted scaling.

## Decision

- Keep the Pt-Consistent Tree as the deployment leader. It remains substantially better for Pt,
  Max. Force, curve prediction, and interval sharpness.
- Use Hybrid v2 as the new Deep Learning reference challenger. It is the strongest neural candidate
  on Type accuracy, Pt error, curve error, and calibrated 90% coverage.
- Preserve GointMLP v2 as an ablation showing the value of fold-local response pretraining, but do not
  expose it as an additional production choice.
- Do not change the production model registry, endpoints, or UI from this experiment.
- The next neural experiment should target Max. Force specifically, using a development-only loss
  ablation or residual head. It must not select settings from the reused fixed benchmark.

## Evidence Boundary

The 546-row fixed benchmark has been reused by earlier project experiments. It supports internal
regression comparisons but is not a pristine external validation set. Publication-grade claims still
require a newly generated untouched simulation campaign collected after the final protocol is frozen.
