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

if /I "%APP_ENV%"=="dev" (
  echo.
  if "%STARTUP_VENV_SYNC%"=="0" (
    .venv\Scripts\python.exe scripts\sync_dev_venv.py --profile dev
  ) else (
    .venv\Scripts\python.exe scripts\sync_dev_venv.py --profile dev --sync
  )
  if errorlevel 1 echo WARNING: The virtual environment differs from the dependency lock; continuing startup.
)

if /I "%APP_ENV%"=="dev" if not "%STARTUP_UPDATE_CHECK%"=="0" (
  echo.
  echo Dependency freshness check:
  call scripts\check_updates.bat --no-python
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
