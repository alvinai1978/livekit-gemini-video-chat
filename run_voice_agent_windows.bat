@echo off
setlocal
cd /d "%~dp0agent"
if not exist .env copy .env.example .env

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py -3.12
) else (
  set PY=python
)

if not exist .venv (
  echo Creating Python virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto failed

python -m ensurepip --upgrade
python -m pip install -U pip setuptools wheel
python -m pip install -U -r requirements.txt
if errorlevel 1 goto failed

python -c "from livekit import agents; from livekit.plugins import google; print('OK: Agent dependencies ready')"
if errorlevel 1 goto failed

python agent.py dev
goto end

:failed
echo.
echo Agent failed to start. Try running fix_agent_windows.bat first.

:end
pause
