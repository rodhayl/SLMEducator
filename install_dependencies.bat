@echo off
setlocal EnableExtensions

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

echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo WARNING: Failed to upgrade pip (continuing anyway)
) else (
    echo pip upgraded successfully.
)
echo.

if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
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

python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing uvicorn...
    pip install uvicorn
    if errorlevel 1 (
        echo ERROR: Failed to install uvicorn
        exit /b 1
    )
    echo uvicorn installed successfully.
) else (
    echo uvicorn is already available.
)
echo.

echo Dependency setup complete.
exit /b 0
