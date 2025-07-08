@echo off
echo Setting up Payment Regression AI POC with MySQL

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.9+ and add it to PATH
    exit /b 1
)

REM Check if MySQL is running
echo Checking MySQL connection...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo Warning: MySQL client not found in PATH
    echo Please ensure MySQL is installed and running
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create directories
echo Creating directories...
if not exist "logs" mkdir logs
if not exist "database\migrations" mkdir database\migrations
if not exist "database\seeds" mkdir database\seeds
if not exist "tests\generated" mkdir tests\generated

REM Copy environment file
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo Please update .env file with your MySQL credentials
)

REM Initialize database
echo Initializing database...
python database\init_db.py

REM Initialize git repository
git init >nul 2>&1
git add . >nul 2>&1
git commit -m "Initial commit - Payment system with MySQL setup" >nul 2>&1

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Update .env file with your MySQL credentials
echo 2. Run: venv\Scripts\activate.bat
echo 3. Run: python src\payment_service\api.py
echo 4. Test: python src\utils\sample_data.py
echo.
echo API will be available at: http://localhost:5000