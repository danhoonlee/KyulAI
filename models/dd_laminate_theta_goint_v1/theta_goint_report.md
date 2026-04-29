# DD Theta Goint Classifier Report

This is a GointMLP-inspired theta-only deep model: multi-branch JointMLP-style head plus auxiliary ordinal loss.
It uses only `theta1` and `theta2`, normalized by 90 degrees.

## Deep Theta Result

Validation mode: `sample`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| theta_goint | 0.9450 ± 0.0257 | 0.9512 ± 0.0241 | 0.9456 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[123   3   0]
 [ 17 215   2]
 [  0   0  40]]
```

## Classical Theta-Only Comparison

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| extra_trees | 0.9600 ± 0.0184 | 0.9675 ± 0.0151 | 0.9600 |
| neural_net_mlp_lbfgs | 0.9600 ± 0.0200 | 0.9667 ± 0.0172 | 0.9596 |
| hist_gradient_boosting | 0.9650 ± 0.0122 | 0.9644 ± 0.0213 | 0.9646 |
| random_forest | 0.9575 ± 0.0170 | 0.9626 ± 0.0179 | 0.9574 |
| neural_net_mlp_adam | 0.9225 ± 0.0527 | 0.9198 ± 0.0534 | 0.9217 |
| svc_rbf | 0.8850 ± 0.0483 | 0.8758 ± 0.0587 | 0.8866 |
