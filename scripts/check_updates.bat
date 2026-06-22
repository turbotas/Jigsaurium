@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul 2>&1 || (
  echo Failed to access repository root from script path.
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
  set "PYTHON_CMD=python"
)

%PYTHON_CMD% -m pip list --outdated
set "UPDATES_EXIT=%ERRORLEVEL%"

where npm >nul 2>&1
if not errorlevel 1 (
  echo.
  echo GOV.UK frontend npm update status:
  npm outdated govuk-frontend
)

popd
exit /b %UPDATES_EXIT%
