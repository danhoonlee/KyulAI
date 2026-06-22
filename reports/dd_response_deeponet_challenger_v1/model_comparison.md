# DD Laminate Response DL Challengers v1

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Feature set: `theta_physics_nn_v2`
- Samples: 900
- Validation: GroupKFold by theta pair, 5 folds
- Curve target: direct 128-point normalized force curve head
- Output artifacts: `models/dd_laminate_response_deeponet_challenger_v1`

## Fair Comparison Contract

All trained DL challengers keep the same comparison surface as `response_goint_physics_nn_v2`:

- Input features are fixed to `theta_physics_nn_v2` unless explicitly overridden.
- Scalar targets are fixed to log-normalized `pt`, `max_displacement`, and `max_force`.
- Curve targets are fixed to the direct normalized response curve head, not the Tree/PCA surrogate.
- Loss terms keep the same class, ordinal, scalar, and curve weighting contract as the GointMLP trainer.
- `physics_guided_mlp` keeps the same targets but adds soft output-shape penalties for curve start, peak normalization, monotonicity, and smoothness.
- `deeponet_response` uses a DeepONet-style branch/trunk factorization to generate the response curve as a learned function on the displacement grid.
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
| deeponet_response | trained | 0.9400 | 0.9370 | 990.16 | 1799.71 | 0.07994 | 2765.28 | 4.57 | 0.0229 | 163016 | 0.640 |
| stack_lstm | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gru | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gnn | skipped: not selected |  |  |  |  |  |  |  |  |  |  |
| stack_gat | skipped: not selected |  |  |  |  |  |  |  |  |  |  |

## Recommendation

`deeponet_response` is the best DL challenger in this run, but it does not clearly beat `response_goint_physics_nn_v2` across the main response metrics.

No backend model key or UI/API default was changed in this pass.
