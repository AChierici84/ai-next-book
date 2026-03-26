@echo off
setlocal

cd /d "%~dp0web"

echo [1/2] Eseguo build...
call npm run build
if errorlevel 1 (
  echo Build fallita. Interruzione.
  exit /b %errorlevel%
)

echo [2/2] Avvio dev server...
call npm run dev

endlocal
