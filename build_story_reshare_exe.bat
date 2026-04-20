@echo off
setlocal

if not exist .venv (
  py -3.9 -m venv .venv
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r requirements.txt
"%VENV_PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name InstagramStoryReshare run_story_reshare_ui.py

echo.
echo Build finished. Executable should be under dist\InstagramStoryReshare.exe
