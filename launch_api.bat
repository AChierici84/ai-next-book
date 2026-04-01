@echo off
setlocal

cd /d "%~dp0api"

set "PY_EXE=.venv_new\Scripts\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=.venv\Scripts\python.exe"

if not exist "%PY_EXE%" (
  echo Ambiente Python non trovato in api\.venv_new
  echo Esegui prima:
  echo   py -3.12 -m venv api\.venv_new
  echo   api\.venv_new\Scripts\python.exe -m pip install -r api\requirements.txt
  exit /b 1
)

echo [API] Avvio FastAPI su http://127.0.0.1:8001 ...
call "%PY_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

endlocal
