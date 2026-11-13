@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>&1 || (
  echo Failed to access repository root from script path.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run scripts\setup_venv.bat first.
  popd
  exit /b 1
)

if "%APP_ENV%"=="" set "APP_ENV=dev"

.venv\Scripts\python.exe scripts\warn_if_migrations_pending.py

if /I "%APP_ENV%"=="dev" if not "%STARTUP_UPDATE_CHECK%"=="0" (
  echo.
  echo Dependency freshness check:
  call scripts\check_updates.bat
  if errorlevel 1 echo WARNING: Dependency update check encountered an issue; continuing startup.
)

if /I "%APP_ENV%"=="dev" (
  .venv\Scripts\python.exe -m flask --app run:app run --host 0.0.0.0 --reload --no-debugger
) else (
  .venv\Scripts\python.exe -m flask --app run:app run --host 0.0.0.0
)
set "APP_EXIT=%ERRORLEVEL%"
popd
exit /b %APP_EXIT%
