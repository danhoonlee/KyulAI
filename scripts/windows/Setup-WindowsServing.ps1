param(
    [string]$Python = "py -3.11",
    [switch]$SkipTorch,
    [ValidateSet("cpu", "cuda")]
    [string]$TorchBackend = "cpu",
    [string]$TorchVersion = "2.2.0",
    [string]$TorchCpuIndexUrl = "https://download.pytorch.org/whl/cpu",
    [string]$TorchCudaIndexUrl = "https://download.pytorch.org/whl/cu121"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

function Invoke-ConfiguredPython {
    param(
        [string]$Arguments
    )

    Invoke-Expression "$Python $Arguments"
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $Python $Arguments"
    }
}

Write-Host "Project root: $ProjectRoot"
Write-Host "Checking Python command: $Python"
Invoke-ConfiguredPython "--version"

Write-Host "Creating virtual environment..."
Invoke-ConfiguredPython "-m venv .venv"

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment Python was not created at $VenvPython"
}

function Invoke-VenvPython {
    param(
        [string[]]$Arguments
    )

    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Virtualenv Python command failed: python $($Arguments -join ' ')"
    }
}

try {
    Invoke-VenvPython -Arguments @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)")
} catch {
    throw "Python 3.11 or newer is required. Install Python 3.11 x64 and rerun this script."
}

Invoke-VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-VenvPython -Arguments @("-m", "pip", "install", "-r", "requirements-serving.txt")

if (-not $SkipTorch) {
    if ($TorchBackend -eq "cuda") {
        Write-Host "Installing PyTorch CUDA wheel..."
        Invoke-VenvPython -Arguments @("-m", "pip", "install", "torch==$TorchVersion", "--index-url", $TorchCudaIndexUrl)
    } else {
        Write-Host "Installing PyTorch CPU wheel..."
        Invoke-VenvPython -Arguments @("-m", "pip", "install", "torch==$TorchVersion", "--index-url", $TorchCpuIndexUrl)
    }
}

Write-Host "Verifying runtime imports..."
Invoke-VenvPython -Arguments @("-c", "import fastapi, uvicorn, joblib, numpy, sklearn; print('api/classical deps ok')")
if (-not $SkipTorch) {
    Invoke-VenvPython -Arguments @("-c", "import torch; print('torch ok', torch.__version__); print('cuda available', torch.cuda.is_available()); print('cuda device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')")
}

Write-Host "Checking package consistency..."
Invoke-VenvPython -Arguments @("-m", "pip", "check")

Write-Host "Checking model readiness summary..."
Invoke-VenvPython -Arguments @("-c", "from src.backend.api.v1.dd_laminate import warm_prediction_models; from src.backend.api.v1.simple_injection import model_availability_status; print('dd:', warm_prediction_models()); print('injection:', model_availability_status())")

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "  1. Copy .env.windows.example to .env.local and fill Slack values if needed."
Write-Host "  2. Start servers with scripts\windows\Start-All.ps1 -SkipCloudflare for local-only testing."
Write-Host "  3. Verify with scripts\windows\Check-Health.ps1 -Ready."
