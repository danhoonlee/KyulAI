# Windows GPU PC Handoff

This package is intended for moving the current DD Laminate / Injection runtime
to a Windows PC and optionally running heavier Laminate distillation training on
an NVIDIA GPU.

## Included Current State

- DD Laminate web runtime
- Simple Injection web runtime
- Current active Laminate/u3/Injection models
- Current XAI reports
- RAG knowledge index and docs
- Windows serving scripts
- Laminate distillation training script
- GPU training helper script

Current visible Laminate Forecast models:

- `response_surrogate_physics_v2` / Laminate Forecast - Machine Learning
- `response_goint_physics_nn_v2` / Laminate Forecast - Deep Learning
- `response_distilled_grid_conf_v1` / Laminate Forecast - Distilled NN v3

Current Distilled NN v3 metrics:

- Type accuracy: `0.9789`
- Macro F1: `0.9784`
- Pt MAE: `469.74 kips`
- Curve normalized RMSE: `0.00977`

## Fresh Windows Setup

Install these first:

- Git for Windows
- Python 3.11 x64
- NVIDIA driver

Then open PowerShell in the extracted project folder.

For GPU training:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\Setup-WindowsServing.ps1 -TorchBackend cuda
```

The setup output should show:

```text
cuda available True
cuda device <your NVIDIA GPU name>
```

If CUDA is not visible, the code will still run, but training will fall back to
CPU and the 2.5-degree grid run may take a long time.

## Run Local Servers

```powershell
.\scripts\windows\Start-All.ps1 -SkipCloudflare
```

Open:

- DD Laminate: `http://127.0.0.1:8000`
- Simple Injection: `http://127.0.0.1:8010`

Health check:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```

## Run GPU Distillation

The helper script runs the heavier 2.5-degree confidence-weighted synthetic grid
distillation pass with `--device auto`.

```powershell
.\scripts\windows\Train-LaminateDistillationGPU.ps1
```

Expected startup line on an NVIDIA GPU:

```text
Using device: cuda (...)
```

Default output folder:

```text
models\dd_laminate_response_distilled_grid_gpu_v1
```

You can customize the run:

```powershell
.\scripts\windows\Train-LaminateDistillationGPU.ps1 `
  -GridStep 2.5 `
  -SyntheticWeight 0.28 `
  -ConfidencePower 1.5 `
  -BatchSize 512 `
  -OutputDir models\dd_laminate_response_distilled_grid_gpu_v1
```

## After Training

Check the metrics:

```powershell
Get-Content models\dd_laminate_response_distilled_grid_gpu_v1\response_distilled_metrics.json
```

If the new model beats the current v3, copy or register it as the next visible
model key in `src/backend/api/v1/dd_laminate.py`, then regenerate its XAI prior.

## Notes

- CPU serving and GPU training use the same codebase.
- `--device auto` chooses CUDA first, then Apple MPS, then CPU.
- The current Windows setup installs CUDA PyTorch only when
  `-TorchBackend cuda` is passed.
- `.env.local` is optional for local prediction. Use it only for secrets such as
  Slack/OpenAI/Cloudflare settings.
