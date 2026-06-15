param(
    [string]$Python = "py -3.11",
    [switch]$SkipTorch
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"
Write-Host "Creating virtual environment..."
Invoke-Expression "$Python -m venv .venv"

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements-serving.txt

if (-not $SkipTorch) {
    Write-Host "Installing PyTorch CPU wheel..."
    & $VenvPython -m pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
}

Write-Host "Verifying runtime imports..."
& $VenvPython -c "import fastapi, uvicorn, joblib, numpy, sklearn; print('api/classical deps ok')"
if (-not $SkipTorch) {
    & $VenvPython -c "import torch; print('torch ok', torch.__version__)"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next: copy .env.windows.example to .env.local and fill Slack values if needed."
