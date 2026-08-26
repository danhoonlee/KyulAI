@echo off
setlocal

set "WSL_EXE=C:\Windows\System32\wsl.exe"

"%WSL_EXE%" -d Ubuntu -- bash -lc "systemctl --user --no-pager status imperialax-laminate.service imperialax-injection.service cafedecafe-nangman.service cafedecafe-nangman-sync.timer imperialax-serving-backup.timer imperialax-cloudflared.service cafedecafe-cloudflared.service"
echo.
echo External health checks
curl.exe -fsS https://laminate.imperialax.com/health
echo.
curl.exe -fsS https://injection.imperialax.com/health
echo.
curl.exe -fsS https://nangman.cafedecafe.co.kr/health
echo.
pause
