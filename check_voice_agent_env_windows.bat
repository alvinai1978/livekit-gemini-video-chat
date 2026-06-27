@echo off
cd /d "%~dp0agent"
if not exist .venv (
  py -3.12 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U python-dotenv >nul
python check_agent_env.py
pause
