@echo off
setlocal

cd /d "%~dp0rag"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python non trovato in rag\.venv
  echo Esegui prima:
  echo   py -3.12 -m venv rag\.venv
  echo   rag\.venv\Scripts\pip install -r rag\requirements.txt
  exit /b 1
)

echo [API] Avvio FastAPI su http://127.0.0.1:8001 ...
call ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

endlocal
