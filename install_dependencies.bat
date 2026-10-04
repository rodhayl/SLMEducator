@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo SLMEducator - Dependency Installation
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

echo Python version:
python --version
echo.

if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created successfully!
) else (
    echo Virtual environment already exists.
)
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)
echo Virtual environment activated!
echo.

if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        echo Please check requirements.txt for any issues
        exit /b 1
    )
    echo Dependencies installed successfully!
) else (
    echo WARNING: requirements.txt not found, skipping dependency installation
)
echo.

if /I "%1"=="--dev" (
    python -m pip install -r requirements-dev.txt
    if errorlevel 1 exit /b 1
)
python -m pip check
if errorlevel 1 exit /b 1

echo Dependency setup complete.
exit /b 0
