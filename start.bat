@echo off
REM SLMEducator Start Script
REM This script sets up the environment and starts the FastAPI application

echo ========================================
echo SLMEducator - Setup and Launch Script
echo ========================================
echo.

REM Install dependencies and prepare environment
if not exist "install_dependencies.bat" (
    echo ERROR: install_dependencies.bat not found.
    pause
    exit /b 1
)

call install_dependencies.bat
if %errorlevel% neq 0 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated!
echo.

REM Create necessary directories
echo Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "exports" mkdir exports
if not exist "temp" mkdir temp
echo Directories created!
echo.

REM Set environment variables
set SLM_ENV=development
set SLM_LOG_LEVEL=INFO
set SLM_DB_PATH=slm_educator.db
set SLM_LOG_DIR=logs
set SLM_DATA_DIR=data
set SLM_EXPORTS_DIR=exports
set SLM_TEMP_DIR=temp

if "%SLM_INITIAL_ADMIN_PASSWORD%"=="" (
    set "SLM_INITIAL_ADMIN_PASSWORD=Admin12345678"
)
if "%SLM_INITIAL_ADMIN_EMAIL%"=="" (
    set "SLM_INITIAL_ADMIN_EMAIL=admin@example.invalid"
)
python scripts\seed_admin.py
if errorlevel 1 (
    echo ERROR: Admin seeding failed.
    pause
    exit /b 1
)

echo Environment variables set.
echo.

echo ========================================
echo Starting SLMEducator application...
echo ========================================
echo.
echo Application will be available at: http://127.0.0.1:8080
echo Press Ctrl+C to stop the application
echo.

REM Open browser after a short delay (in background)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8080"

REM Start the FastAPI application using uvicorn
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload

REM Check if application started successfully
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo ERROR: Application failed to start!
    echo ========================================
    echo.
    echo Troubleshooting tips:
    echo 1. Check the logs in the 'logs' directory for error messages
    echo 2. Ensure all dependencies are installed correctly
    echo 3. Check that Python 3.10+ is installed
    echo 4. Verify that port 8080 is not in use
    echo 5. Check that the database file is not corrupted
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Application stopped.
echo ========================================
echo.
pause
