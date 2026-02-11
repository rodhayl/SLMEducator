@echo off
setlocal EnableExtensions

set "MODE=full"
set "NO_COVERAGE=0"
set "OPEN_COVERAGE=0"
set "ASSUME_YES=0"
set "MAXFAIL="

if "%~1"=="" goto :show_help_no_args

:parse_args
if "%~1"=="" goto :validate_args

if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help

if /i "%~1"=="--full" (
    set "MODE=full"
    shift
    goto :parse_args
)
if /i "%~1"=="--quick" (
    set "MODE=quick"
    shift
    goto :parse_args
)
if /i "%~1"=="--ai" (
    set "MODE=ai"
    shift
    goto :parse_args
)
if /i "%~1"=="--phases" (
    set "MODE=phases"
    shift
    goto :parse_args
)
if /i "%~1"=="--real-ai" (
    set "MODE=real-ai"
    shift
    goto :parse_args
)

if /i "%~1"=="--no-coverage" (
    set "NO_COVERAGE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--open-coverage" (
    set "OPEN_COVERAGE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--yes" (
    set "ASSUME_YES=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--maxfail" (
    if "%~2"=="" (
        echo ERROR: --maxfail requires a number.
        goto :show_help_error
    )
    set "MAXFAIL=%~2"
    shift
    shift
    goto :parse_args
)

echo ERROR: Unknown argument: %~1
goto :show_help_error

:validate_args
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Missing virtual environment at venv\Scripts\activate.bat
    echo Dependencies are required before running tests.
    if not exist "install_dependencies.bat" (
        echo ERROR: install_dependencies.bat was not found.
        echo Please create the virtual environment and install dependencies manually.
        exit /b 1
    )
    echo Dependencies are missing. Would you like to install them now? ^(Y/N^)
    choice /C YN /N /M "Select [Y/N]: "
    if errorlevel 2 (
        echo Exiting without running tests.
        exit /b 1
    )
    goto :install_dependencies
)

:activate_environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

python -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo ERROR: pytest is not installed in the active environment.
    echo Run install_dependencies.bat and try again.
    exit /b 1
)

set "PYTEST_BASE=-v --tb=short -ra"
if defined MAXFAIL (
    set "PYTEST_BASE=%PYTEST_BASE% --maxfail=%MAXFAIL%"
)

if /i "%MODE%"=="full" goto :run_full
if /i "%MODE%"=="quick" goto :run_quick
if /i "%MODE%"=="ai" goto :run_ai
if /i "%MODE%"=="phases" goto :run_phases
if /i "%MODE%"=="real-ai" goto :run_real_ai

echo ERROR: Unsupported mode: %MODE%
exit /b 1

:install_dependencies
call install_dependencies.bat
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    exit /b 1
)
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment still missing after installation.
    exit /b 1
)
goto :activate_environment

:run_full
echo Running full test suite...
if "%NO_COVERAGE%"=="1" (
    pytest tests/ %PYTEST_BASE%
) else (
    pytest tests/ %PYTEST_BASE% --cov=src/core --cov-report=term-missing --cov-report=html:htmlcov
)
set "TEST_EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_quick
echo Running quick test suite...
if not defined MAXFAIL (
    pytest tests/ %PYTEST_BASE% --maxfail=3
) else (
    pytest tests/ %PYTEST_BASE%
)
set "TEST_EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_ai
echo Running AI test suite...
pytest tests/ai %PYTEST_BASE% -s
set "TEST_EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_phases
echo Running phase test suite...
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TEST_EXIT_CODE=0"
python tests/features/test_phases_1_2.py
if errorlevel 1 set "TEST_EXIT_CODE=1"
python tests/features/test_phase3_4.py
if errorlevel 1 set "TEST_EXIT_CODE=1"
goto :finish

:run_real_ai
echo WARNING: Real AI tests make external API calls and may incur cost.
if not "%ASSUME_YES%"=="1" (
    set /p CONFIRM=Continue with real AI tests? Type YES to continue: 
    if /i not "%CONFIRM%"=="YES" (
        echo Real AI test run cancelled.
        exit /b 0
    )
)

set USE_REAL_AI=1
set NO_MOCKS_ALLOWED=1
pytest tests/real_ai/ %PYTEST_BASE% --capture=no -s --strict-markers
set "TEST_EXIT_CODE=%ERRORLEVEL%"
goto :finish

:finish
echo.
if "%TEST_EXIT_CODE%"=="0" (
    echo Test run completed successfully.
) else (
    echo Test run failed with exit code %TEST_EXIT_CODE%.
)

if "%OPEN_COVERAGE%"=="1" (
    if exist "htmlcov\index.html" (
        start "" "htmlcov\index.html"
    ) else (
        echo Coverage report not found: htmlcov\index.html
    )
)

exit /b %TEST_EXIT_CODE%

:show_help_no_args
set "HELP_EXIT_CODE=0"
echo No arguments provided.
echo.
goto :show_help_common

:show_help
set "HELP_EXIT_CODE=0"
goto :show_help_common

:show_help_error
set "HELP_EXIT_CODE=1"
echo.
:show_help_common
echo Usage:
echo   run_tests.bat [MODE] [OPTIONS]
echo.
echo Modes (pick one):
echo   --full       Run full suite in tests/ (default mode when provided explicitly)
echo   --quick      Run full suite without coverage, quick defaults
echo   --ai         Run tests/ai only
echo   --phases     Run phase-specific feature tests
echo   --real-ai    Run real AI tests in tests/real_ai (network and cost risk)
echo.
echo Options:
echo   --maxfail N       Stop after N failures
echo   --no-coverage     Disable coverage (only applies to --full)
echo   --open-coverage   Open htmlcov\index.html after run if it exists
echo   --yes             Skip real-AI confirmation prompt (use with --real-ai)
echo   -h, --help        Show this help message
echo.
echo Examples:
echo   run_tests.bat --full
echo   run_tests.bat --quick --maxfail 2
echo   run_tests.bat --ai
echo   run_tests.bat --phases
echo   run_tests.bat --real-ai --yes
echo   run_tests.bat --full --open-coverage
echo.
exit /b %HELP_EXIT_CODE%
