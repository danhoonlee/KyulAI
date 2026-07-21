# RTX Resource Benchmark - 20260721_resource_benchmark_v1

Short benchmark on the Windows WSL RTX worker to compare PyTorch DataLoader worker settings after adding resource controls.

## Environment

- Worker: `user@100.65.153.56`
- GPU: `NVIDIA GeForce RTX 5070`
- Batch size: `512`
- Epochs per smoke case: `3`
- CV splits for Goint smoke: `2`
- Pin memory: `auto`

## Results

| Stage | Workers | Seconds |
| --- | ---: | ---: |
| Distillation final-only | 0 | 5 |
| Distillation final-only | 1 | 6 |
| Distillation final-only | 2 | 5 |
| Distillation final-only | 4 | 6 |
| Geometry GointMLP CV smoke | 0 | 3 |
| Geometry GointMLP CV smoke | 1 | 4 |
| Geometry GointMLP CV smoke | 2 | 4 |
| Geometry GointMLP CV smoke | 4 | 4 |

## Recommendation

- Keep `NUM_WORKERS=2` as the default for longer RTX runs because it is stable and slightly helps the distillation path without overloading CPU.
- Use `NUM_WORKERS=0` if the Windows PC needs to stay more responsive while training.
- Avoid `NUM_WORKERS=4` for the current dataset size; the added worker overhead did not improve runtime in this smoke benchmark.
- Keep `TREE_N_JOBS=8` as a balanced default. Lower to `4` if sklearn Tree or fold-local teacher stages make the PC feel sluggish.

## Source

- Raw CSV: `resource_benchmark.csv`
