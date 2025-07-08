@echo off
echo Starting Payment API Server...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure your MySQL settings
    pause
    exit /b 1
)

REM Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

REM Start the application using the main runner
python run_server.py

pause