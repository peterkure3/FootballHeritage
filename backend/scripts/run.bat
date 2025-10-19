@echo off
REM Set working directory to backend folder
cd /d "%~dp0"

REM Load environment variables from .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "%%a=%%b"
)

REM Run the application
target\release\football-heritage-backend.exe

pause
