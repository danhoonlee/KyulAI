param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8010
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

. (Join-Path $PSScriptRoot "Import-EnvFile.ps1") -Path (Join-Path $ProjectRoot ".env.local")

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run scripts\windows\Setup-WindowsServing.ps1 first."
}

& $Python -m uvicorn src.backend.simple_injection_app:app --host $HostName --port $Port
