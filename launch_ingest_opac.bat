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

if "%~1"=="" (
  echo [INGEST] Nessun argomento specificato. Avvio ingest con i default di ingest_opac.py
  echo [INGEST] Esempio personalizzato:
  echo   .\launch_ingest_opac.bat --start-year 2026 --end-year 2024 --max-pages-per-year 3
) else (
  echo [INGEST] Avvio ingest OPAC con argomenti: %*
)

call ".venv\Scripts\python.exe" ingest_opac.py %*

endlocal
