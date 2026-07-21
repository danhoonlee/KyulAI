# Windows WSL GPU Worker

This note records how the Windows RTX PC is used as a remote GPU worker for KyulAI / ImperialAX development.

## Current Worker

- Host: `user@100.65.153.56`
- Access network: Tailscale
- SSH key on Mac/Codex side: `~/.ssh/kyulai_wsl_gpu_codex`
- Remote project: `~/projects/KyulAI`
- Current verified commit: `27f43b3`
- Verified runtime:
  - Python `3.11.15`
  - PyTorch `2.11.0+cu128`
  - CUDA available: `true`
  - GPU: `NVIDIA GeForce RTX 5070`

## One-Line Remote Command

From the Mac/local repo:

```bash
scripts/remote/Run-WSLGPU.sh 'python --version'
```

The wrapper automatically:

1. Connects to `user@100.65.153.56` with `~/.ssh/kyulai_wsl_gpu_codex`.
2. Enters `~/projects/KyulAI`.
3. Activates `.venv`.
4. Runs the command passed as the argument.

## Typical Flow

Refresh code and models on the worker:

```bash
scripts/remote/Run-WSLGPU.sh 'git pull && git lfs pull'
```

Check GPU:

```bash
scripts/remote/Run-WSLGPU.sh 'python - <<'"'"'PY'"'"'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY'
```

Check GPU utilization from WSL:

```bash
scripts/remote/Run-WSLGPU.sh '/usr/lib/wsl/lib/nvidia-smi'
```

Watch it live after connecting directly through SSH:

```bash
watch -n 1 /usr/lib/wsl/lib/nvidia-smi
```

Run a training script:

```bash
scripts/remote/Run-WSLGPU.sh 'python scripts/dd_response_distillation_train.py --help'
```

Run the Laminate RTX strict validation with balanced resource controls:

```bash
scripts/remote/Run-WSLGPU.sh 'RUN_ID=manual_geometry_strict TREE_N_JOBS=8 NUM_WORKERS=2 bash scripts/remote/Run-LaminateGeometryStrictRTX.sh'
```

Run with lower CPU pressure:

```bash
scripts/remote/Run-WSLGPU.sh 'RUN_ID=manual_geometry_strict_light TREE_N_JOBS=4 NUM_WORKERS=0 bash scripts/remote/Run-LaminateGeometryStrictRTX.sh'
```

Run a short resource benchmark:

```bash
scripts/remote/Run-WSLGPU.sh 'RUN_ID=manual_resource_benchmark CONFIGS=0:auto,2:auto EPOCHS=3 SPLITS=2 BATCH_SIZE=512 bash scripts/remote/Benchmark-LaminateRTXResources.sh'
```

After training, commit/push results from either the remote worker or local Mac after pulling/copying the outputs.

## Notes

- `nvidia-smi` may not be on the WSL shell `PATH`, but PyTorch CUDA was verified and works.
- For WSL, `/usr/lib/wsl/lib/nvidia-smi` is the most reliable explicit path.
- Laminate training still uses CPU heavily during sklearn `ExtraTrees`, PCA, synthetic grid generation, and Tree teacher pseudo-labeling. CUDA is used by the PyTorch GointMLP / Hybrid Student sections.
- Current balanced defaults: `TREE_N_JOBS=8`, `NUM_WORKERS=2`, `PIN_MEMORY=auto`, `PREFETCH_FACTOR=2`.
- Keep secrets out of Git. Do not commit `.env.local` or local SQLite auth DBs.
- Large model artifacts should use the targeted Git LFS paths already configured in `.gitattributes`.
