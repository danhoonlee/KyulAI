# DD Theta-Only Type Predictor Report

Dataset: `data/datasets/DD_curated_csv_v1`

This model predicts Type 1/2/3 using only `theta1`, `theta2`, and `case`. It does not use Pt or force-displacement curves.
Because this is a pre-Abaqus surrogate, performance is expected to be lower than curve-based models.

## Label Counts

- Type 1: 126
- Type 2: 234
- Type 3: 40

## Intrinsic Ambiguity

There are 2 theta pairs with conflicting labels across Case3/Case4.
The deterministic theta-only ceiling on the 400-row dataset is approximately 0.9950 if one label must be assigned per theta pair.

| theta1 | theta2 | samples |
|---:|---:|---|
| 73 | -45 | Case3/Test_078=Type2; Case4/Test_078=Type1 |
| -52 | 62 | Case3/Test_152=Type2; Case4/Test_152=Type1 |

## Primary Sample CV

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| hist_gradient_boosting | 0.9625 ± 0.0158 | 0.9624 ± 0.0250 | 0.9622 |
| neural_net_mlp_adam | 0.9025 ± 0.0184 | 0.9072 ± 0.0244 | 0.9015 |
| neural_net_mlp_lbfgs | 0.9000 ± 0.0335 | 0.8980 ± 0.0306 | 0.8993 |
| random_forest | 0.9125 ± 0.0177 | 0.8927 ± 0.0179 | 0.9125 |
| extra_trees | 0.8775 ± 0.0289 | 0.8601 ± 0.0320 | 0.8796 |
| svc_rbf | 0.8575 ± 0.0451 | 0.8410 ± 0.0451 | 0.8587 |

## Secondary Grouped CV

This grouped check keeps matching Case3/Case4 Test_ID pairs together and is the better estimate for unseen theta pairs.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_adam | 0.9025 ± 0.0556 | 0.9133 ± 0.0459 | 0.9026 |
| neural_net_mlp_lbfgs | 0.8975 ± 0.0348 | 0.9055 ± 0.0391 | 0.8978 |
| random_forest | 0.9175 ± 0.0423 | 0.8799 ± 0.0721 | 0.9164 |
| extra_trees | 0.9025 ± 0.0357 | 0.8672 ± 0.0708 | 0.9063 |
| hist_gradient_boosting | 0.8950 ± 0.0551 | 0.8352 ± 0.0746 | 0.8929 |
| svc_rbf | 0.8625 ± 0.0468 | 0.8339 ± 0.0724 | 0.8663 |

Selected production theta/case model: `hist_gradient_boosting` from primary CV.

## Selected Model Confusion Matrix

Rows=true, columns=predicted `[Type1, Type2, Type3]`.

```text
[[118   8   0]
 [  5 229   0]
 [  0   2  38]]
```
