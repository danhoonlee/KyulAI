# DD CSV Curve Classifier Report

Dataset: `data/datasets/DD_curated_csv_v1`

This model classifies DD laminate response Type 1/2/3 from raw force-displacement CSV-derived shape features.
The validation uses StratifiedGroupKFold grouped by `Test_ID`, so matching Case3/Case4 tests do not leak across train/validation folds.

## Label Counts

- Type 1: 126
- Type 2: 234
- Type 3: 40

## Feature Columns

`transition_x_ratio`, `transition_load_ratio`, `post_fraction`, `post_slope_ratio`, `post_slope_drop`, `post_r2`, `post_nrmse`, `tail_r2`, `abs_quad_a`, `slope_drift`, `mean_abs_curvature`, `max_abs_curvature`, `data_quality_code`

## Cross-Validation Summary

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| random_forest | 0.9675 ± 0.0367 | 0.9738 ± 0.0264 | 0.9674 |
| hist_gradient_boosting | 0.9600 ± 0.0436 | 0.9690 ± 0.0304 | 0.9595 |
| extra_trees | 0.9575 ± 0.0415 | 0.9661 ± 0.0281 | 0.9572 |
| svc_rbf | 0.9575 ± 0.0257 | 0.9578 ± 0.0152 | 0.9581 |

Selected model: `random_forest`

## Selected Model Confusion Matrix

Rows are true labels, columns are predictions `[Type1, Type2, Type3]`.

```text
[[120   6   0]
 [  6 228   0]
 [  0   1  39]]
```
