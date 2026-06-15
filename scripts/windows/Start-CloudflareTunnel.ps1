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

$Cloudflared = "cloudflared.exe"
& $Cloudflared --config $ConfigPath tunnel run kclab-composite-ai
