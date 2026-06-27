@echo off
cd /d "%~dp0backend"
if not exist .env copy .env.example .env
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -U pip
python -m pip install -U -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
pause
