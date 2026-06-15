param(
    [string]$CloudflareConfig = ""
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

if ($CloudflareConfig) {
    Start-KyulProcess -Name "cloudflared" -Script (Join-Path $PSScriptRoot "Start-CloudflareTunnel.ps1") -Arguments "-ConfigPath `"$CloudflareConfig`""
} else {
    Start-KyulProcess -Name "cloudflared" -Script (Join-Path $PSScriptRoot "Start-CloudflareTunnel.ps1")
}

Write-Host ""
Write-Host "Started. Logs are in: $LogDir"
Write-Host "Run scripts\windows\Check-Health.ps1 to verify."
