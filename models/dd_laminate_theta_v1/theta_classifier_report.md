# DD Theta-Only Type Predictor Report

Dataset: `data/datasets/DD_curated_csv_v2`

This model predicts Type 1/2/3 using only `theta1`, `theta2`, and `case`. It does not use Pt or force-displacement curves.
Because this is a pre-Abaqus surrogate, performance is expected to be lower than curve-based models.

## Label Counts

- Type 1: 160
- Type 2: 291
- Type 3: 49

## Intrinsic Ambiguity

There are 2 theta pairs with conflicting labels across Case3/Case4.
The deterministic theta-only ceiling on the 500-row dataset is approximately 0.9960 if one label must be assigned per theta pair.

| theta1 | theta2 | samples |
|---:|---:|---|
| 73 | -45 | Case3/Test_078=Type2; Case4/Test_078=Type1 |
| -52 | 62 | Case3/Test_152=Type2; Case4/Test_152=Type1 |

## Primary Sample CV

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| hist_gradient_boosting | 0.9640 ± 0.0136 | 0.9579 ± 0.0184 | 0.9637 |
| random_forest | 0.9320 ± 0.0133 | 0.9195 ± 0.0331 | 0.9314 |
| neural_net_mlp_lbfgs | 0.9220 ± 0.0098 | 0.9194 ± 0.0173 | 0.9216 |
| extra_trees | 0.8980 ± 0.0271 | 0.8817 ± 0.0344 | 0.8993 |
| neural_net_mlp_adam | 0.8900 ± 0.0303 | 0.8812 ± 0.0386 | 0.8891 |
| svc_rbf | 0.8340 ± 0.0273 | 0.8158 ± 0.0374 | 0.8373 |

## Secondary Grouped CV

This grouped check keeps matching Case3/Case4 Test_ID pairs together and is the better estimate for unseen theta pairs.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_lbfgs | 0.9255 ± 0.0335 | 0.9180 ± 0.0458 | 0.9246 |
| hist_gradient_boosting | 0.9298 ± 0.0337 | 0.9152 ± 0.0431 | 0.9292 |
| random_forest | 0.9255 ± 0.0283 | 0.9109 ± 0.0326 | 0.9250 |
| neural_net_mlp_adam | 0.8993 ± 0.0431 | 0.8867 ± 0.0564 | 0.8983 |
| extra_trees | 0.8917 ± 0.0230 | 0.8720 ± 0.0301 | 0.8925 |
| svc_rbf | 0.8438 ± 0.0390 | 0.8192 ± 0.0346 | 0.8461 |

Selected production theta/case model: `hist_gradient_boosting` from primary CV.

## Selected Model Confusion Matrix

Rows=true, columns=predicted `[Type1, Type2, Type3]`.

```text
[[154   6   0]
 [  7 283   1]
 [  0   4  45]]
```
