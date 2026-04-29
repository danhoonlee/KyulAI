# DD Theta-Only Type Predictor Report

Dataset: `data/datasets/DD_curated_csv_v1`

This model predicts Type 1/2/3 using only `theta1` and `theta2`. It does not use case, Pt, or force-displacement curves.
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
| extra_trees | 0.9600 ± 0.0184 | 0.9675 ± 0.0151 | 0.9600 |
| neural_net_mlp_lbfgs | 0.9600 ± 0.0200 | 0.9667 ± 0.0172 | 0.9596 |
| hist_gradient_boosting | 0.9650 ± 0.0122 | 0.9644 ± 0.0213 | 0.9646 |
| random_forest | 0.9575 ± 0.0170 | 0.9626 ± 0.0179 | 0.9574 |
| neural_net_mlp_adam | 0.9225 ± 0.0527 | 0.9198 ± 0.0534 | 0.9217 |
| svc_rbf | 0.8850 ± 0.0483 | 0.8758 ± 0.0587 | 0.8866 |

## Secondary Grouped CV

This grouped check keeps matching Case3/Case4 Test_ID pairs together and is the better estimate for unseen theta pairs.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_adam | 0.9150 ± 0.0496 | 0.9188 ± 0.0522 | 0.9141 |
| neural_net_mlp_lbfgs | 0.8900 ± 0.0215 | 0.8807 ± 0.0507 | 0.8892 |
| random_forest | 0.9100 ± 0.0457 | 0.8730 ± 0.0731 | 0.9091 |
| extra_trees | 0.8900 ± 0.0184 | 0.8705 ± 0.0449 | 0.8874 |
| svc_rbf | 0.8800 ± 0.0615 | 0.8570 ± 0.0908 | 0.8824 |
| hist_gradient_boosting | 0.8900 ± 0.0629 | 0.8313 ± 0.0793 | 0.8879 |

Selected production theta-only model: `extra_trees` from primary CV.

## Selected Model Confusion Matrix

Rows=true, columns=predicted `[Type1, Type2, Type3]`.

```text
[[119   7   0]
 [  9 225   0]
 [  0   0  40]]
```
