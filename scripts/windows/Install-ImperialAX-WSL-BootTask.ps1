#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$TaskName = "ImperialAX WSL Serving",
    [string]$Distro = "Ubuntu",
    [string]$LinuxUser = "user"
)

$ErrorActionPreference = "Stop"

$WindowsIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$WslExe = Join-Path $env:WINDIR "System32\wsl.exe"
$Services = @(
    "imperialax-laminate.service",
    "imperialax-injection.service",
    "cafedecafe-nangman.service",
    "cafedecafe-nangman-sync.timer",
    "imperialax-serving-backup.timer",
    "imperialax-cloudflared.service",
    "cafedecafe-cloudflared.service"
) -join " "

$LinuxCommand = "systemctl --user start $Services"
$ActionArguments = "-d $Distro -u $LinuxUser -- bash -lc `"$LinuxCommand`""
$Action = New-ScheduledTaskAction -Execute $WslExe -Argument $ActionArguments
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal `
    -UserId $WindowsIdentity `
    -LogonType S4U `
    -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Start ImperialAX and CafeDeCafe WSL services before interactive login."

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 3
$Registered = Get-ScheduledTask -TaskName $TaskName
$Info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "Scheduled task installed: $($Registered.TaskName)" -ForegroundColor Green
Write-Host "State: $($Registered.State)"
Write-Host "Last result: $($Info.LastTaskResult)"

