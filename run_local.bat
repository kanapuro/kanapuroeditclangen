@echo off
set ROOT=%~dp0
if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%ROOT%main.py" %*
) else if exist "C:\Users\henry.brown2\python-3.11.9-embed-amd64\python.exe" (
  "C:\Users\henry.brown2\python-3.11.9-embed-amd64\python.exe" "%ROOT%main.py" %*
) else (
  echo No suitable Python found. Activate a venv or install Python and retry.
  pause
)
