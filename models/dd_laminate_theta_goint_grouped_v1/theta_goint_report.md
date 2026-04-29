# DD Theta Goint Classifier Report

This is a GointMLP-inspired theta-only deep model: multi-branch JointMLP-style head plus auxiliary ordinal loss.
It uses only `theta1` and `theta2`, normalized by 90 degrees.

## Deep Theta Result

Validation mode: `grouped`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| theta_goint | 0.9050 ± 0.0595 | 0.8989 ± 0.0758 | 0.9071 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[118   8   0]
 [ 24 204   6]
 [  0   0  40]]
```

## Classical Theta-Only Comparison

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_adam | 0.9150 ± 0.0496 | 0.9188 ± 0.0522 | 0.9141 |
| neural_net_mlp_lbfgs | 0.8900 ± 0.0215 | 0.8807 ± 0.0507 | 0.8892 |
| random_forest | 0.9100 ± 0.0457 | 0.8730 ± 0.0731 | 0.9091 |
| extra_trees | 0.8900 ± 0.0184 | 0.8705 ± 0.0449 | 0.8874 |
| svc_rbf | 0.8800 ± 0.0615 | 0.8570 ± 0.0908 | 0.8824 |
| hist_gradient_boosting | 0.8900 ± 0.0629 | 0.8313 ± 0.0793 | 0.8879 |
