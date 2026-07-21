param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [double]$GridStep = 2.5,
    [double]$SyntheticWeight = 0.28,
    [double]$ConfidencePower = 1.5,
    [int]$Epochs = 190,
    [int]$FinalEpochs = 150,
    [int]$BatchSize = 512,
    [string]$OutputDir = "models\dd_laminate_response_distilled_grid_gpu_v1"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

if (-not (Test-Path $Python)) {
    throw "Python executable not found at $Python. Run the Windows setup script first, or pass -Python <path>."
}

Write-Host "Checking PyTorch CUDA visibility..."
& $Python -c "import torch; print('torch:', torch.__version__); print('cuda_available:', torch.cuda.is_available()); print('cuda_device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'warning: CUDA is not visible. Training will fall back to CPU if --device auto is used.')"

Write-Host "Starting Laminate Forecast distillation training with auto device selection..."
& $Python scripts\dd_response_distillation_train.py `
    --device auto `
    --model-name laminate_forecast_distilled_grid_gpu_v1 `
    --synthetic-grid-step $GridStep `
    --synthetic-weight $SyntheticWeight `
    --synthetic-confidence-power $ConfidencePower `
    --synthetic-min-confidence-weight 0.45 `
    --epochs $Epochs `
    --final-epochs $FinalEpochs `
    --patience 30 `
    --batch-size $BatchSize `
    --hidden-dim 80 `
    --branches 8 `
    --dropout 0.08 `
    --lr 6e-4 `
    --weight-decay 7e-4 `
    --output-dir $OutputDir

Write-Host "Training complete. Output: $OutputDir"
