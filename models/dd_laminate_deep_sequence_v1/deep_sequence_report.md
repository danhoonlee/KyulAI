# DD Goint Sequence Classifier Report

This is a DD-specific, GointMLP-inspired deep learning model: GRU sequence encoder + JointMLP-style multi-branch head + auxiliary ordinal loss.

## Input

Each force-displacement CSV is resampled to a fixed sequence. Per timestep features are:

`displacement_norm`, `load_norm`, `step_norm`, `theta1/90`, `theta2/90`, `pt/pt_scale`, `case_id`, `load/pt`

## Deep Model Result

Validation mode: `sample`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| dd_goint_sequence | 0.9775 ± 0.0094 | 0.9819 ± 0.0075 | 0.9777 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[125   1   0]
 [  8 226   0]
 [  0   0  40]]
```

## Comparison With Existing Models

Primary table below is from the existing `models/dd_laminate_csv_meta_v1` combined metadata+curve feature run.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| hist_gradient_boosting | 0.9950 ± 0.0100 | 0.9958 ± 0.0083 | 0.9949 |
| random_forest | 0.9925 ± 0.0100 | 0.9938 ± 0.0083 | 0.9924 |
| extra_trees | 0.9800 ± 0.0061 | 0.9838 ± 0.0050 | 0.9801 |
| neural_net_mlp_lbfgs | 0.9550 ± 0.0257 | 0.9576 ± 0.0226 | 0.9547 |
| svc_rbf | 0.9575 ± 0.0127 | 0.9515 ± 0.0221 | 0.9582 |
| neural_net_mlp_adam | 0.9425 ± 0.0232 | 0.9222 ± 0.0395 | 0.9411 |
