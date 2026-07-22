param(
    [string]$OutputDir = ".\dist\windows\LaminateForecast-existing-win-x64-portable",
    [int]$Port = 8765,
    [switch]$SkipInstall,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Info($message) {
    Write-Host "[Laminate EXE] $message" -ForegroundColor Cyan
}

$Root = (Resolve-Path ".").Path
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputPath = Join-Path $Root $OutputDir
$BuildPath = Join-Path $Root "build\laminate-exe"

Info "Project root: $Root"
Info "Output: $OutputPath"

if (-not (Test-Path ".\.venv")) {
    Info "Creating Python 3.11 virtual environment"
    py -3.11 -m venv .venv
}

Info "Activating virtual environment"
& ".\.venv\Scripts\Activate.ps1"

if (-not $SkipInstall) {
    Info "Installing runtime and packaging dependencies"
    python -m pip install --upgrade pip
    pip install -r ".\requirements-serving.txt"
    pip install -r ".\requirements-ml.txt"
    pip install pyinstaller requests
}

if (-not $SkipBuild) {
    Info "Building backend executable"
    pyinstaller `
        --clean `
        --noconfirm `
        --name laminate_backend `
        --onefile `
        --paths "$Root" `
        --distpath "$BuildPath\backend" `
        --workpath "$BuildPath\pyinstaller-backend" `
        "$ScriptDir\laminate_backend_launcher.py"

    Info "Building desktop launcher executable"
    pyinstaller `
        --clean `
        --noconfirm `
        --name LaminateForecast `
        --onefile `
        --paths "$Root" `
        --distpath "$BuildPath\launcher" `
        --workpath "$BuildPath\pyinstaller-launcher" `
        "$ScriptDir\laminate_desktop_launcher.py"
}

Info "Creating portable bundle"
if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
New-Item -ItemType Directory -Force -Path "$OutputPath\backend" | Out-Null

Copy-Item "$BuildPath\backend\laminate_backend.exe" "$OutputPath\backend\laminate_backend.exe" -Force
Copy-Item "$BuildPath\launcher\LaminateForecast.exe" "$OutputPath\LaminateForecast.exe" -Force

Info "Copying existing app source, frontend, data, and model artifacts"
Copy-Item ".\src" "$OutputPath\src" -Recurse -Force
Copy-Item ".\data" "$OutputPath\data" -Recurse -Force
Copy-Item ".\models" "$OutputPath\models" -Recurse -Force
Copy-Item ".\requirements-serving.txt" "$OutputPath\requirements-serving.txt" -Force
Copy-Item ".\requirements-ml.txt" "$OutputPath\requirements-ml.txt" -Force

@"
Laminate Forecast Windows Portable
==================================

Run:
  LaminateForecast.exe

Default local URL:
  http://127.0.0.1:$Port

Security mode:
  - LAMINATE_REQUIRE_AUTH=1
  - IMPERIALAX_DISABLE_DEMO_LOGIN=1
  - Users must sign in with module.laminate entitlement.

Account storage:
  The local SQLite auth database is created under runtime/auth unless IMPERIALAX_AUTH_DB is set.
  Create/recover users with the bundled admin/API workflow before sharing externally.
"@ | Set-Content -Path "$OutputPath\README.txt" -Encoding UTF8

Info "Done:"
Write-Host (Resolve-Path $OutputPath).Path -ForegroundColor Green
