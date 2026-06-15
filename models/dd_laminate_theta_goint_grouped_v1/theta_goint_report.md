# DD Theta Goint Classifier Report

This is a GointMLP-inspired theta/case deep model: multi-branch JointMLP-style head plus auxiliary ordinal loss.
It uses only pre-Abaqus inputs: `theta1`, `theta2`, and `case`.

## Deep Theta Result

Validation mode: `grouped`; folds: 5

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| theta_goint | 0.8975 ± 0.0439 | 0.8901 ± 0.0445 | 0.8978 |

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[153   7   0]
 [ 32 248  11]
 [  0   1  48]]
```

## Classical Theta-Only Comparison

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_lbfgs | 0.9255 ± 0.0335 | 0.9180 ± 0.0458 | 0.9246 |
| hist_gradient_boosting | 0.9298 ± 0.0337 | 0.9152 ± 0.0431 | 0.9292 |
| random_forest | 0.9255 ± 0.0283 | 0.9109 ± 0.0326 | 0.9250 |
| neural_net_mlp_adam | 0.8993 ± 0.0431 | 0.8867 ± 0.0564 | 0.8983 |
| extra_trees | 0.8917 ± 0.0230 | 0.8720 ± 0.0301 | 0.8925 |
| svc_rbf | 0.8438 ± 0.0390 | 0.8192 ± 0.0346 | 0.8461 |
