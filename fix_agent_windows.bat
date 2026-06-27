@echo off
setlocal
cd /d "%~dp0agent"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py -3.12
) else (
  set PY=python
)

if not exist .env copy .env.example .env

echo.
echo [1/5] Creating/refreshing Python virtual environment...
if exist .venv rmdir /s /q .venv
%PY% -m venv .venv
if errorlevel 1 goto failed

call .venv\Scripts\activate.bat
if errorlevel 1 goto failed

echo.
echo [2/5] Enabling pip inside the virtual environment...
python -m ensurepip --upgrade
if errorlevel 1 goto failed
python -m pip install -U pip setuptools wheel
if errorlevel 1 goto failed

echo.
echo [3/5] Removing conflicting LiveKit packages if present...
python -m pip uninstall -y livekit livekit-api livekit-agents livekit-plugins-google >nul 2>nul

echo.
echo [4/5] Installing LiveKit Agents with Google/Gemini plugin...
python -m pip install -U "livekit-agents[google]~=1.5" python-dotenv
if errorlevel 1 goto failed

echo.
echo [5/5] Checking import...
python -c "from livekit import agents; from livekit.plugins import google; print('OK: LiveKit Agents + Google plugin installed')"
if errorlevel 1 goto failed

echo.
echo DONE. Now run: run_voice_agent_windows.bat
goto end

:failed
echo.
echo FAILED. Please copy the full error above and send it.

:end
pause
