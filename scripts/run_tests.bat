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

.venv\Scripts\python.exe -m pytest -p no:cacheprovider %*
set "TEST_EXIT=%ERRORLEVEL%"
popd
exit /b %TEST_EXIT%
