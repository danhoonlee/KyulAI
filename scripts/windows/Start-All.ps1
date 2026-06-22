param(
    [string]$CloudflareConfig = "",
    [switch]$SkipCloudflare,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Start-KyulProcess {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Arguments = ""
    )
    $log = Join-Path $LogDir "$Name.log"
    $err = Join-Path $LogDir "$Name.err.log"
    $command = "-NoProfile -ExecutionPolicy Bypass -File `"$Script`" $Arguments"
    Write-Host "Starting $Name..."
    Start-Process powershell.exe -ArgumentList $command -WorkingDirectory $ProjectRoot -RedirectStandardOutput $log -RedirectStandardError $err
}

Start-KyulProcess -Name "dd" -Script (Join-Path $PSScriptRoot "Start-DD.ps1")
Start-KyulProcess -Name "injection" -Script (Join-Path $PSScriptRoot "Start-Injection.ps1")

if (-not $SkipCloudflare) {
    if (-not $CloudflareConfig) {
        $CloudflareConfig = Join-Path $ProjectRoot "infrastructure\cloudflare\kclab-composite-ai.windows.yml"
    }

    if (Test-Path $CloudflareConfig) {
        Start-KyulProcess -Name "cloudflared" -Script (Join-Path $PSScriptRoot "Start-CloudflareTunnel.ps1") -Arguments "-ConfigPath `"$CloudflareConfig`""
    } else {
        Write-Warning "Cloudflare config not found: $CloudflareConfig"
        Write-Warning "Skipping tunnel startup. Use -SkipCloudflare for local-only runs or create the config from the .example.yml file."
    }
} else {
    Write-Host "Skipping Cloudflare tunnel startup."
}

Write-Host ""
Write-Host "Started. Logs are in: $LogDir"
if (-not $SkipHealthCheck) {
    Write-Host "Waiting for local readiness..."
    & (Join-Path $PSScriptRoot "Check-Health.ps1") -Ready -LocalOnly -Retries 6 -RetryDelaySec 5
} else {
    Write-Host "Run scripts\windows\Check-Health.ps1 -Ready to verify."
}
