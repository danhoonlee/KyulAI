# DD Laminate Response DL Challengers v1

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Feature set: `theta_physics_nn_v2`
- Samples: 900
- Validation: GroupKFold by theta pair, 5 folds
- Curve target: direct 128-point normalized force curve head
- Output artifacts: `models/dd_laminate_response_pca_curve_challenger_v2`

## Fair Comparison Contract

All trained DL challengers keep the same comparison surface as `response_goint_physics_nn_v2`:

- Input features are fixed to `theta_physics_nn_v2` unless explicitly overridden.
- Scalar targets are fixed to log-normalized `pt`, `max_displacement`, and `max_force`.
- Curve targets are fixed to the direct normalized response curve head, not the Tree/PCA surrogate.
- Loss terms keep the same class, ordinal, scalar, and curve weighting contract as the GointMLP trainer.
- `physics_guided_mlp` keeps the same targets but adds soft output-shape penalties for curve start, peak normalization, monotonicity, and smoothness.
- `deeponet_response` uses a DeepONet-style branch/trunk factorization to generate the response curve as a learned function on the displacement grid.
- `pca_curve_mlp` fits a train-fold-only PCA/POD curve basis and predicts basis coefficients before reconstructing the full curve.
- Stack LSTM/GRU/GNN/GAT candidates add only deterministic 16-ply stack features derived from the same theta/case input.
- The intended variable is the neural architecture replacing the GointMLP-style branch mixer.

## Reference Models

| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |
|---|---:|---:|---:|---:|---:|---:|
| response_surrogate_physics_v2 | 0.9422 | 0.9372 | 438.15 | 338.93 | 0.00701 | 479.43 |
| response_goint_physics_nn_v2 | 0.9389 | 0.9383 | 661.41 | 1160.28 | 0.02131 | 1250.71 |

## Challenger Results

| Candidate | Status | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE | Train s | Infer ms/sample | Params | Size MB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| plain_mlp | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| residual_mlp | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| gated_mlp | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| physics_guided_mlp | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| deeponet_response | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| pca_curve_mlp | trained | 0.9189 | 0.9132 | 558.50 | 799.43 | 0.01176 | 837.49 | 5.93 | 0.0293 | 120218 | 0.491 |
| stack_lstm | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gru | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gnn | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gat | skipped: not selected |  |  |  |  |  |  |  |  |  |  |

## Recommendation

`pca_curve_mlp` beats the current GointMLP reference on Pt and normalized curve RMSE, but should remain research-only until API compatibility and the tree reference comparison are reviewed.

No backend model key or UI/API default was changed in this pass.
