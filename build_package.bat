@echo off
setlocal EnableDelayedExpansion

echo ===================================================
echo SLM Educator - Build Package Script
echo ===================================================

REM Check for virtual environment
set "VENV_DIR=venv"
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo [WARN] Virtual environment 'venv' not found.
    echo Assuming globally installed dependencies...
)

REM Check for PyInstaller
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller is not installed or not in PATH.
    echo Please run: pip install pyinstaller
    if "%1"=="" pause
    exit /b 1
)

REM Process arguments
if "%1"=="--prod" goto production
if "%1"=="--test" goto test
if "%1"=="--help" goto help

:menu
echo.
echo Select Build Mode:
echo 1. Production (Clean install, empty database)
echo 2. Test (Include current working database)
echo 3. Exit
echo.
set /p mode="Enter choice (1-3): "

if "%mode%"=="1" goto production
if "%mode%"=="2" goto test
if "%mode%"=="3" goto end
echo Invalid choice. Exiting.
goto end

:production
set "BUILD_NAME=SLMEducator"
set "INCLUDE_DB=0"
echo.
echo [MODE] Production: Building clean version with default empty database.
goto build

:test
set "BUILD_NAME=SLMEducator_Test"
set "INCLUDE_DB=1"
echo.
echo [MODE] Test: Building version with current database included.
goto build

:build
echo.
echo.
echo [1/3] Cleaning previous builds...

REM Kill any running instances first to unlock files
taskkill /F /IM "%BUILD_NAME%.exe" >nul 2>&1
taskkill /F /IM "SLMEducator.exe" >nul 2>&1
taskkill /F /IM "SLMEducator_Test.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

REM Clean directories (robust retry if locked)
if exist "build" rmdir /s /q "build"
if exist "dist\%BUILD_NAME%" (
    rmdir /s /q "dist\%BUILD_NAME%"
    if exist "dist\%BUILD_NAME%" (
        timeout /t 2 /nobreak >nul
        rmdir /s /q "dist\%BUILD_NAME%"
    )
)
if exist "%BUILD_NAME%.spec" del /q "%BUILD_NAME%.spec"

if "%SLM_INITIAL_ADMIN_PASSWORD%"=="" (
    set "SLM_INITIAL_ADMIN_PASSWORD=Admin12345678"
)
if "%SLM_INITIAL_ADMIN_EMAIL%"=="" (
    set "SLM_INITIAL_ADMIN_EMAIL=admin@example.invalid"
)
if not exist "env.properties" (
    if exist "env.properties.example" (
        echo [INFO] env.properties not found. Creating it from env.properties.example...
        copy /Y "env.properties.example" "env.properties" >nul
        if errorlevel 1 (
            echo [ERROR] Failed to create env.properties from env.properties.example.
            if "%1"=="" pause
            exit /b 1
        )
    ) else (
        echo [ERROR] Missing both env.properties and env.properties.example.
        echo Please add env.properties.example to the repository.
        if "%1"=="" pause
        exit /b 1
    )
)

echo.
echo [2/3] Running PyInstaller...
echo This may take a moment...

REM --onedir: Create a directory with exe and deps
REM --windowed: No console window (GUI app)
REM --clean: Clean PyInstaller cache
REM --noconfirm: overwrite output directory
REM --add-data: include non-binary resources
REM Note: Using semicolon ; for Windows separator in add-data
pyinstaller --noconfirm --onedir --windowed --name "%BUILD_NAME%" --clean ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.scrolledtext" ^
    --add-data "src;src" ^
    --add-data "src/api/dependencies.py;src/api" ^
    --add-data "translations;translations" ^
    --add-data "env.properties;." ^
    --add-data "alembic.ini;." ^
    --add-data "alembic;alembic" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "sqlalchemy.sql.default_comparator" ^
    --hidden-import "sqlalchemy.ext.baked" ^
    --hidden-import "sqlite3" ^
    --hidden-import "fastapi" ^
    --hidden-import "fastapi.staticfiles" ^
    --hidden-import "fastapi.responses" ^
    --hidden-import "fastapi.security" ^
    --hidden-import "pydantic" ^
    --hidden-import "pydantic.v1" ^
    --hidden-import "pydantic.v1.typing" ^
    --hidden-import "pydantic.v1.fields" ^
    --hidden-import "pydantic.v1.main" ^
    --hidden-import "pydantic.v1.types" ^
    --hidden-import "pydantic.v1.validators" ^
    --hidden-import "email_validator" ^
    --hidden-import "multipart" ^
    --hidden-import "python_multipart" ^
    --hidden-import "cryptography" ^
    --hidden-import "cryptography.fernet" ^
    --hidden-import "jwt" ^
    --hidden-import "passlib" ^
    --hidden-import "passlib.hash" ^
    --hidden-import "httpx" ^
    --hidden-import "langsmith" ^
    --hidden-import "langchain_core" ^
    --hidden-import "langchain_openai" ^
    --hidden-import "typing_extensions" ^
    --hidden-import "anyio" ^
    --hidden-import "starlette" ^
    --hidden-import "starlette.middleware" ^
    --hidden-import "starlette.middleware.cors" ^
    --hidden-import "websockets" ^
    --hidden-import "click" ^
    --hidden-import "h11" ^
    --hidden-import "sniffio" ^
    --hidden-import "src.api.dependencies" ^
    --hidden-import "src.api.routes.auth" ^
    --hidden-import "src.api.routes.dashboard" ^
    --hidden-import "src.api.routes.content" ^
    --hidden-import "src.api.routes.ai" ^
    --hidden-import "src.api.routes.settings" ^
    --hidden-import "src.api.routes.generation" ^
    --hidden-import "src.api.routes.assessment" ^
    --hidden-import "src.api.routes.learning" ^
    --hidden-import "src.api.routes.mastery" ^
    --hidden-import "src.api.routes.classroom" ^
    --hidden-import "src.api.routes.study_plans" ^
    --hidden-import "src.api.routes.gamification" ^
    --hidden-import "src.api.routes.annotations" ^
    --hidden-import "src.api.routes.upload" ^
    --hidden-import "src.api.routes.students" ^
    --hidden-import "src.core.services.auth" ^
    --hidden-import "src.core.services.database" ^
    --hidden-import "src.core.services.ai_service" ^
    --collect-all "fastapi" ^
    --collect-all "pydantic" ^
    --collect-all "sqlalchemy" ^
    --collect-all "cryptography" ^
    src/starter.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    if "%1"=="" pause
    exit /b 1
)

 echo.
 echo [3/3] Finalizing package...
 
 if "%INCLUDE_DB%"=="1" (
     echo Copying current database for Test mode...
     if exist "slm_educator.db" (
        copy /Y "slm_educator.db" "dist\%BUILD_NAME%\slm_educator.db" >nul
        echo Database copied.
        
        REM Copy WAL/SHM files if they exist (for active SQLite connections)
        if exist "slm_educator.db-wal" copy /Y "slm_educator.db-wal" "dist\%BUILD_NAME%" >nul
        if exist "slm_educator.db-shm" copy /Y "slm_educator.db-shm" "dist\%BUILD_NAME%" >nul
    ) else (
        echo [WARN] slm_educator.db not found in working directory!
    )
) else (
    echo Creating fresh database with initial admin user for Production build...
    
    REM Remove any existing database first
    if exist "slm_educator.db" del /Q "slm_educator.db"
    if exist "slm_educator.db-wal" del /Q "slm_educator.db-wal"
    if exist "slm_educator.db-shm" del /Q "slm_educator.db-shm"
    
    REM Create database and seed initial admin user
    python scripts\seed_admin.py
    if errorlevel 1 (
        echo [WARN] Failed to seed admin user, database will be created on first run
    ) else (
        echo Database created with initial admin user
    )
    
    REM Copy the seeded database to dist
    if exist "slm_educator.db" (
        copy /Y "slm_educator.db" "dist\%BUILD_NAME%\slm_educator.db" >nul
        echo Database copied to distribution.
    ) else (
        echo [WARN] Database file not created, will be created on first run
    )
    
    echo.
    echo ============================================
    echo INITIAL ADMIN CREDENTIALS:
    echo Username: admin
    echo Password: printed by scripts\seed_admin.py
    echo or sourced from SLM_INITIAL_ADMIN_PASSWORD if set
    echo IMPORTANT: Change credentials immediately after first login.
    echo ============================================
)

REM Ensure the packaged web UI matches the current source tree.
REM This must run AFTER PyInstaller COLLECT and any DB copy to avoid overwrites.
set /a _sync_wait=0
:wait_for_web
if exist "dist\%BUILD_NAME%\_internal\src\web" goto do_web_sync
set /a _sync_wait+=1
if %_sync_wait% GEQ 10 goto no_web_sync
timeout /t 1 /nobreak >nul
goto wait_for_web

:do_web_sync
echo Syncing web assets into dist...
robocopy "src\web" "dist\%BUILD_NAME%\_internal\src\web" /MIR /NFL /NDL /NJH /NJS /NP >nul
REM Robocopy exit codes 0-7 indicate success (including "some files copied").
if errorlevel 8 (
    echo [WARN] Web asset sync reported errors (robocopy exit %errorlevel%)
) else (
    echo [INFO] Web assets synced.
)
goto web_sync_done

:no_web_sync
echo [WARN] Dist web directory not found; skipping web asset sync.

:web_sync_done

echo.
echo ===================================================
echo BUILD SUCCESSFUL
echo ===================================================
echo Output directory: dist\%BUILD_NAME%
echo Executable: dist\%BUILD_NAME%\%BUILD_NAME%.exe
echo.
if "%1"=="" pause
goto end

:help
echo Usage: build_package.bat [OPTIONS]
echo.
echo Options:
echo   --prod    Build for Production (Clean install, empty database)
echo   --test    Build for Test (Include current working database)
echo   --help    Show this help message
goto end

:end
endlocal
exit /b 0
