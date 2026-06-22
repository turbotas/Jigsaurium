@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul 2>&1 || (
  echo Failed to access repository root from script path.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run scripts\setup_venv.bat first.
  popd
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo npm is required to update GOV.UK frontend assets.
  popd
  exit /b 1
)

set "TARGET_VERSION=%~1"
if "%TARGET_VERSION%"=="" set "TARGET_VERSION=latest"

.venv\Scripts\python.exe scripts\vendor_govuk_assets.py --update %TARGET_VERSION%
set "UPDATE_EXIT=%ERRORLEVEL%"
popd
exit /b %UPDATE_EXIT%
