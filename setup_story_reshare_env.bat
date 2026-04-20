@echo off
setlocal

if not exist .venv (
  py -3.9 -m venv .venv
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r requirements.txt

echo.
echo Virtual environment ready in .venv
echo Activate with: .venv\Scripts\activate
