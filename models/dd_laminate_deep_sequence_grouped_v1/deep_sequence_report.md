# DD Goint Sequence Classifier Report

This is a DD-specific, GointMLP-inspired deep learning model: GRU sequence encoder + JointMLP-style multi-branch head + auxiliary ordinal loss.

## Input

Each force-displacement CSV is resampled to a fixed sequence. Per timestep features are:

`displacement_norm`, `load_norm`, `step_norm`, `theta1/90`, `theta2/90`, `pt/pt_scale`, `case_id`, `load/pt`

## Deep Model Result

Validation mode: `grouped`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| dd_goint_sequence | 0.9739 ± 0.0148 | 0.9703 ± 0.0252 | 0.9738 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[160   0   0]
 [ 11 280   0]
 [  0   2  47]]
```

## Comparison With Existing Models

Primary table below is from the existing `models/dd_laminate_csv_meta_v1` combined metadata+curve feature run.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| random_forest | 0.9960 ± 0.0049 | 0.9967 ± 0.0040 | 0.9960 |
| hist_gradient_boosting | 0.9940 ± 0.0080 | 0.9898 ± 0.0166 | 0.9938 |
| extra_trees | 0.9820 ± 0.0075 | 0.9834 ± 0.0079 | 0.9821 |
| neural_net_mlp_adam | 0.9760 ± 0.0120 | 0.9715 ± 0.0172 | 0.9760 |
| neural_net_mlp_lbfgs | 0.9660 ± 0.0206 | 0.9622 ± 0.0254 | 0.9660 |
| svc_rbf | 0.9640 ± 0.0136 | 0.9590 ± 0.0189 | 0.9642 |
