# DD CSV Curve Classifier Report

Dataset: `data/datasets/DD_curated_csv_v2`

This model classifies DD laminate response Type 1/2/3 from transition metadata plus raw force-displacement CSV-derived shape features.
Candidate models include tree ensembles, SVC, HistGradientBoosting, and neural-network MLP baselines.
Feature set: `combined`.
Primary validation mode: `sample`. `sample` uses shuffled StratifiedKFold; `grouped` keeps matching Case3/Case4 Test_ID pairs together.

## Label Counts

- Type 1: 160
- Type 2: 291
- Type 3: 49

## Feature Columns

`theta1`, `theta2`, `pt`, `case_id`, `transition_x_ratio`, `transition_load_ratio`, `post_fraction`, `post_slope_ratio`, `post_slope_drop`, `post_r2`, `post_nrmse`, `tail_r2`, `abs_quad_a`, `slope_drift`, `mean_abs_curvature`, `max_abs_curvature`, `data_quality_code`

## Cross-Validation Summary

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| random_forest | 0.9960 ± 0.0049 | 0.9967 ± 0.0040 | 0.9960 |
| hist_gradient_boosting | 0.9940 ± 0.0080 | 0.9898 ± 0.0166 | 0.9938 |
| extra_trees | 0.9820 ± 0.0075 | 0.9834 ± 0.0079 | 0.9821 |
| neural_net_mlp_adam | 0.9760 ± 0.0120 | 0.9715 ± 0.0172 | 0.9760 |
| neural_net_mlp_lbfgs | 0.9660 ± 0.0206 | 0.9622 ± 0.0254 | 0.9660 |
| svc_rbf | 0.9640 ± 0.0136 | 0.9590 ± 0.0189 | 0.9642 |

## Secondary Conservative Check

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| svc_rbf | 0.9596 ± 0.0305 | 0.9580 ± 0.0415 | 0.9601 |
| random_forest | 0.9703 ± 0.0291 | 0.9547 ± 0.0508 | 0.9698 |
| extra_trees | 0.9660 ± 0.0239 | 0.9511 ± 0.0440 | 0.9654 |
| hist_gradient_boosting | 0.9620 ± 0.0251 | 0.9477 ± 0.0464 | 0.9614 |
| neural_net_mlp_lbfgs | 0.9495 ± 0.0365 | 0.9446 ± 0.0410 | 0.9494 |
| neural_net_mlp_adam | 0.9564 ± 0.0399 | 0.9149 ± 0.1139 | 0.9527 |

Selected model: `random_forest`

## Selected Model Confusion Matrix

Rows are true labels, columns are predictions `[Type1, Type2, Type3]`.

```text
[[158   2   0]
 [  0 291   0]
 [  0   0  49]]
```
