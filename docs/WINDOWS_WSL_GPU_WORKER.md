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

Run a training script:

```bash
scripts/remote/Run-WSLGPU.sh 'python scripts/dd_response_distillation_train.py --help'
```

After training, commit/push results from either the remote worker or local Mac after pulling/copying the outputs.

## Notes

- `nvidia-smi` may not be on the WSL shell `PATH`, but PyTorch CUDA was verified and works.
- Keep secrets out of Git. Do not commit `.env.local` or local SQLite auth DBs.
- Large model artifacts should use the targeted Git LFS paths already configured in `.gitattributes`.
