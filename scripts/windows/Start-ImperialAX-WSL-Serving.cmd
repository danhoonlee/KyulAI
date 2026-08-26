@echo off
setlocal

set "WSL_EXE=C:\Windows\System32\wsl.exe"

"%WSL_EXE%" -d Ubuntu -- bash -lc "systemctl --user start imperialax-laminate.service imperialax-injection.service cafedecafe-nangman.service cafedecafe-nangman-sync.timer imperialax-serving-backup.timer imperialax-cloudflared.service cafedecafe-cloudflared.service"
if errorlevel 1 (
  echo ImperialAX WSL services failed to start.
  exit /b 1
)

exit /b 0
