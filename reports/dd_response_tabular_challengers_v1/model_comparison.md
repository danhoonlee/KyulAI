# DD Laminate Response Tabular Challengers v1

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Feature set: `theta_physics_v2`
- Samples: 900
- Validation: GroupKFold by theta pair, 5 folds
- Curve surrogate: PCA on 128-point normalized force curves, 18 components
- Output artifacts: `models/dd_laminate_response_tabular_challengers_v1`

## Fair Comparison Contract

All trained challengers keep the same comparison surface as `response_surrogate_physics_v2`:

- Input features are fixed to `theta_physics_v2`, the compact CLT/ABD physics feature set.
- Scalar targets are fixed to `pt`, `max_displacement`, and `max_force`.
- Curve targets are fixed to normalized force curves on the shared response grid.
- Each challenger fits a PCA curve surrogate with the same component budget and predicts PCA scores.
- The only intended variable is the learner family used for Type, scalar, and curve-score prediction.

## Reference Models

| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |
|---|---:|---:|---:|---:|---:|---:|
| response_surrogate_physics_v2 | 0.9422 | 0.9372 | 438.15 | 338.93 | 0.00701 | 479.43 |
| response_goint_physics_nn_v2 | 0.9389 | 0.9383 | 661.41 | 1160.28 | 0.02131 | 1250.71 |

## Challenger Results

| Candidate | Status | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE | Train s | Infer ms/sample | Size MB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| extra_trees | trained | 0.9456 | 0.9397 | 441.40 | 343.07 | 0.00702 | 484.95 | 2.09 | 0.3177 | 453.149 |
| random_forest | trained | 0.9411 | 0.9352 | 449.94 | 582.70 | 0.00795 | 662.47 | 2.87 | 0.2352 | 215.174 |
| hist_gradient_boosting | trained | 0.9289 | 0.9236 | 500.02 | 434.77 | 0.00774 | 522.95 | 30.19 | 0.2600 | 7.357 |
| ridge_linear | trained | 0.9267 | 0.9195 | 828.57 | 1419.47 | 0.01839 | 1238.76 | 0.05 | 0.0045 | 0.033 |
| elastic_net_linear | trained | 0.9267 | 0.9195 | 818.68 | 1405.90 | 0.01919 | 1231.86 | 0.33 | 0.0110 | 0.056 |
| xgboost | trained | 0.9422 | 0.9371 | 472.34 | 427.89 | 0.00774 | 530.79 | 10.82 | 0.0235 | 11.523 |
| lightgbm | trained | 0.9367 | 0.9320 | 499.55 | 433.77 | 0.00756 | 524.21 | 41.51 | 0.2478 | 22.836 |
| catboost | trained | 0.9411 | 0.9340 | 466.33 | 390.40 | 0.00751 | 502.09 | 6.33 | 0.0158 | 5.422 |
| tabpfn | failed: TabPFNLicenseError: TabPFN requires a one-time license acceptance to download |  |  |  |  |  |  |  |  |  |

## Recommendation

`extra_trees` is the best challenger in this run, but it does not clearly beat `response_surrogate_physics_v2` across Pt, curve, and Type metrics. Do not add a backend key yet.

No backend model key or UI/API default was changed in this pass.
