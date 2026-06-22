param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $ProjectRoot "infrastructure\cloudflare\kclab-composite-ai.windows.yml"
}

if (-not (Test-Path $ConfigPath)) {
    throw "Cloudflare config not found: $ConfigPath. Copy infrastructure\cloudflare\kclab-composite-ai.windows.example.yml and edit credentials-file first."
}

$Cloudflared = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
if (-not $Cloudflared) {
    throw "cloudflared.exe was not found on PATH. Install it with: winget install Cloudflare.cloudflared"
}

& $Cloudflared.Source --config $ConfigPath tunnel run kclab-composite-ai
