@echo off
setlocal

set "INSTALLER=%~dp0Install-ImperialAX-WSL-BootTask.ps1"

if not exist "%INSTALLER%" (
  echo Installer not found: %INSTALLER%
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process PowerShell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%INSTALLER%""'"

if errorlevel 1 (
  echo Boot task installation failed or UAC was cancelled.
  pause
  exit /b 1
)

echo ImperialAX WSL boot task installation finished.
pause
