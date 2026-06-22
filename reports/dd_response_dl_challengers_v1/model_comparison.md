# DD Laminate Response DL Challengers v1

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Feature set: `theta_physics_nn_v2`
- Samples: 900
- Validation: GroupKFold by theta pair, 5 folds
- Curve target: direct 128-point normalized force curve head
- Output artifacts: `models/dd_laminate_response_dl_challengers_v1`

## Fair Comparison Contract

All trained DL challengers keep the same comparison surface as `response_goint_physics_nn_v2`:

- Input features are fixed to `theta_physics_nn_v2` unless explicitly overridden.
- Scalar targets are fixed to log-normalized `pt`, `max_displacement`, and `max_force`.
- Curve targets are fixed to the direct normalized response curve head, not the Tree/PCA surrogate.
- Loss terms keep the same class, ordinal, scalar, and curve weighting contract as the GointMLP trainer.
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
| plain_mlp | trained | 0.9422 | 0.9380 | 936.90 | 1584.68 | 0.02569 | 1544.92 | 3.08 | 0.0156 | 123144 | 0.483 |
| residual_mlp | trained | 0.9411 | 0.9374 | 890.09 | 1578.17 | 0.03672 | 1761.96 | 5.80 | 0.0243 | 354824 | 1.374 |
| gated_mlp | trained | 0.9411 | 0.9396 | 726.62 | 1264.22 | 0.02740 | 1410.40 | 5.40 | 0.0271 | 152488 | 0.603 |
| stack_lstm | trained | 0.9389 | 0.9345 | 821.41 | 1367.91 | 0.02581 | 1380.22 | 20.82 | 0.1818 | 277640 | 1.077 |
| stack_gru | trained | 0.9444 | 0.9415 | 956.10 | 1680.79 | 0.03173 | 1641.90 | 17.93 | 0.1201 | 243080 | 0.945 |
| stack_gnn | trained | 0.9444 | 0.9416 | 973.38 | 1613.52 | 0.03121 | 1667.25 | 5.59 | 0.0290 | 194056 | 0.758 |
| stack_gat | trained | 0.9444 | 0.9391 | 774.76 | 1412.32 | 0.02256 | 1399.98 | 8.33 | 0.0446 | 203784 | 0.797 |

## Recommendation

`gated_mlp` is the best DL challenger in this run, but it does not clearly beat `response_goint_physics_nn_v2` across the main response metrics.

No backend model key or UI/API default was changed in this pass.
