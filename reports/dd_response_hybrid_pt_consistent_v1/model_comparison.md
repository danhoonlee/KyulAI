# DD Laminate Response Hybrid Challenger v1

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Type expert feature set: `theta_physics_v2`
- Pt/curve expert feature set: `theta_physics_nn_v2`
- Samples: 900
- Validation: GroupKFold by theta pair, 5 folds
- Output artifacts: `models/dd_laminate_response_hybrid_pt_consistent_v1`

## Model Contract

`hybrid_type_tree_pca_curve_mlp` is one research bundle with two internal experts:

- Type expert: ExtraTrees classifier on compact CLT/ABD physics features.
- Pt/curve expert: PCA/POD curve-decoder MLP on neural-friendly physics features.
- The public prediction contract can remain one request and one response; only the internal heads are separated.
- PCA/POD basis is fit inside each training fold only during validation.

## Reference Models

| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |
|---|---:|---:|---:|---:|---:|---:|
| response_surrogate_physics_v2 | 0.9422 | 0.9372 | 438.15 | 338.93 | 0.00701 | 479.43 |
| response_goint_physics_nn_v2 | 0.9389 | 0.9383 | 661.41 | 1160.28 | 0.02131 | 1250.71 |
| hybrid_type_tree_pca_curve_mlp | 0.9422 | 0.9372 | 642.84 | 1037.45 | 0.03656 | 1518.48 |

## Recommendation

The hybrid should remain research-only until the Type and curve tradeoff is improved.

No backend model key or UI/API default was changed in this pass.
