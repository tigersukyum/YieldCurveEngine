@echo off
rem CB 이자율 커브 엔진 앱 — 더블클릭하면 로컬 서버가 뜨고 브라우저가 열립니다 (http://127.0.0.1:8765)
cd /d "%~dp0"
python -m cb_valuation.step1_curve.app.server --open
pause
