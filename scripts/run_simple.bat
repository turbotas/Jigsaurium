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

if not exist "instance" mkdir "instance"

if "%APP_ENV%"=="" set "APP_ENV=dev"
if "%SECRET_KEY%"=="" set "SECRET_KEY=change-me-dev"
if "%DATABASE_URL%"=="" set "DATABASE_URL=sqlite+pysqlite:///instance/jigsaurium-simple.db"

set "STFD_ENABLED=0"
set "STFD_ALLOW_LOCAL_LOGIN=0"
set "AI_ENABLED=0"
set "IMAGE_EMBEDDINGS_ENABLED=0"

set "AI_API_KEY="
set "AI_ENDPOINT_URL="
set "AI_MODEL="
set "HF_TOKEN="

.venv\Scripts\python.exe scripts\warn_if_migrations_pending.py

if /I "%APP_ENV%"=="dev" if "%STARTUP_UPDATE_CHECK%"=="1" (
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
