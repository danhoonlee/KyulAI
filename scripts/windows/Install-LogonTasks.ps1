param(
    [string]$CloudflareConfig = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not $CloudflareConfig) {
    $CloudflareConfig = Join-Path $ProjectRoot "infrastructure\cloudflare\kclab-composite-ai.windows.yml"
}

function Register-KyulLogonTask {
    param(
        [string]$TaskName,
        [string]$Script,
        [string]$Arguments = ""
    )

    $taskArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$Script`" $Arguments"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $taskArgs -WorkingDirectory $ProjectRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "KyulAI serving process: $TaskName" `
        -Force | Out-Null

    Write-Host "Registered $TaskName"
}

Register-KyulLogonTask -TaskName "KyulAI-DD" -Script (Join-Path $PSScriptRoot "Start-DD.ps1")
Register-KyulLogonTask -TaskName "KyulAI-Injection" -Script (Join-Path $PSScriptRoot "Start-Injection.ps1")
Register-KyulLogonTask -TaskName "KyulAI-CloudflareTunnel" -Script (Join-Path $PSScriptRoot "Start-CloudflareTunnel.ps1") -Arguments "-ConfigPath `"$CloudflareConfig`""

Write-Host ""
Write-Host "Logon tasks installed. They start when this Windows user logs in."
Write-Host "Start them now with:"
Write-Host "  Start-ScheduledTask -TaskName KyulAI-DD"
Write-Host "  Start-ScheduledTask -TaskName KyulAI-Injection"
Write-Host "  Start-ScheduledTask -TaskName KyulAI-CloudflareTunnel"
