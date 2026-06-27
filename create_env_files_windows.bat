@echo off
setlocal
cd /d "%~dp0"
if not exist backend\.env copy backend\.env.example backend\.env
if not exist agent\.env copy agent\.env.example agent\.env
if not exist frontend\.env copy frontend\.env.example frontend\.env
echo.
echo ENV files are ready:
echo - backend\.env
echo - agent\.env
echo - frontend\.env
echo.
echo Open backend\.env and agent\.env, then replace YOUR_ values with your real LiveKit and Gemini keys.
pause
