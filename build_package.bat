@echo off
setlocal
REM Use the script location, even when invoked from another working directory.
pushd "%~dp0"
if errorlevel 1 exit /b 1

if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"
python scripts\build_package.py %*
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
