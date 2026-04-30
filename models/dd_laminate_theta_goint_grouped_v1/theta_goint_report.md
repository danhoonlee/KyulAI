# DD Theta Goint Classifier Report

This is a GointMLP-inspired theta/case deep model: multi-branch JointMLP-style head plus auxiliary ordinal loss.
It uses only pre-Abaqus inputs: `theta1`, `theta2`, and `case`.

## Deep Theta Result

Validation mode: `grouped`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| theta_goint | 0.9050 ± 0.0451 | 0.8920 ± 0.0752 | 0.9071 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[116  10   0]
 [ 21 206   7]
 [  0   0  40]]
```

## Classical Theta-Only Comparison

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_adam | 0.9025 ± 0.0556 | 0.9133 ± 0.0459 | 0.9026 |
| neural_net_mlp_lbfgs | 0.8975 ± 0.0348 | 0.9055 ± 0.0391 | 0.8978 |
| random_forest | 0.9175 ± 0.0423 | 0.8799 ± 0.0721 | 0.9164 |
| extra_trees | 0.9025 ± 0.0357 | 0.8672 ± 0.0708 | 0.9063 |
| hist_gradient_boosting | 0.8950 ± 0.0551 | 0.8352 ± 0.0746 | 0.8929 |
| svc_rbf | 0.8625 ± 0.0468 | 0.8339 ± 0.0724 | 0.8663 |
