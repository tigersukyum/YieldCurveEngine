@echo off
rem 이자율 커브 엔진 앱 — 더블클릭하면 (1) 예전에 켜 둔 앱 서버를 모두 닫고 (2) 새 서버를 띄운 뒤 (3) 브라우저를 엽니다 (http://127.0.0.1:8765)
cd /d "%~dp0"
echo [1/2] 예전 앱 서버 정리 중...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*step1_curve.app.server*' -and $_.Name -like 'python*' } | ForEach-Object { Write-Host ('  종료: PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo [2/2] 서버 시작 (이 창을 닫으면 앱이 종료됩니다)
python -m cb_valuation.step1_curve.app.server --open
pause
