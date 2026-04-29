# DD CSV Curve Classifier Report

Dataset: `data/datasets/DD_curated_csv_v1`

This model classifies DD laminate response Type 1/2/3 from transition metadata plus raw force-displacement CSV-derived shape features.
Candidate models include tree ensembles, SVC, HistGradientBoosting, and neural-network MLP baselines.
Feature set: `combined`.
Primary validation mode: `sample`. `sample` uses shuffled StratifiedKFold; `grouped` keeps matching Case3/Case4 Test_ID pairs together.

## Label Counts

- Type 1: 126
- Type 2: 234
- Type 3: 40

## Feature Columns

`theta1`, `theta2`, `pt`, `case_id`, `transition_x_ratio`, `transition_load_ratio`, `post_fraction`, `post_slope_ratio`, `post_slope_drop`, `post_r2`, `post_nrmse`, `tail_r2`, `abs_quad_a`, `slope_drift`, `mean_abs_curvature`, `max_abs_curvature`, `data_quality_code`

## Cross-Validation Summary

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| hist_gradient_boosting | 0.9950 ± 0.0100 | 0.9958 ± 0.0083 | 0.9949 |
| random_forest | 0.9925 ± 0.0100 | 0.9938 ± 0.0083 | 0.9924 |
| extra_trees | 0.9800 ± 0.0061 | 0.9838 ± 0.0050 | 0.9801 |
| neural_net_mlp_lbfgs | 0.9550 ± 0.0257 | 0.9576 ± 0.0226 | 0.9547 |
| svc_rbf | 0.9575 ± 0.0127 | 0.9515 ± 0.0221 | 0.9582 |
| neural_net_mlp_adam | 0.9425 ± 0.0232 | 0.9222 ± 0.0395 | 0.9411 |

## Secondary Conservative Check

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| random_forest | 0.9675 ± 0.0367 | 0.9738 ± 0.0264 | 0.9674 |
| hist_gradient_boosting | 0.9650 ± 0.0464 | 0.9710 ± 0.0328 | 0.9645 |
| extra_trees | 0.9575 ± 0.0232 | 0.9640 ± 0.0151 | 0.9574 |
| neural_net_mlp_lbfgs | 0.9475 ± 0.0200 | 0.9491 ± 0.0209 | 0.9481 |
| svc_rbf | 0.9600 ± 0.0348 | 0.9448 ± 0.0614 | 0.9610 |
| neural_net_mlp_adam | 0.9350 ± 0.0561 | 0.9228 ± 0.0683 | 0.9339 |

Selected model: `hist_gradient_boosting`

## Selected Model Confusion Matrix

Rows are true labels, columns are predictions `[Type1, Type2, Type3]`.

```text
[[124   2   0]
 [  0 234   0]
 [  0   0  40]]
```
