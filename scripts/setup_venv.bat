@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul 2>&1 || (
  echo Failed to access repository root from script path.
  exit /b 1
)

set "PROFILE=%~1"
if "%PROFILE%"=="" set "PROFILE=dev"
set "REQ_FILE=requirements\%PROFILE%.txt"
set "KNOWN_GOOD_FILE=requirements\known-good-%PROFILE%.txt"

if not exist "%REQ_FILE%" (
  echo Unknown dependency profile "%PROFILE%".
  echo Expected one of: dev, prod
  popd
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment in .venv
  py -3 -m venv .venv 2>nul || python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo Could not find .venv\Scripts\python.exe
  popd
  exit /b 1
)

echo Installing dependencies using profile: %PROFILE%
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
  popd
  exit /b 1
)

if exist "%KNOWN_GOOD_FILE%" (
  echo Applying known-good constraints: %KNOWN_GOOD_FILE%
  .venv\Scripts\python.exe -m pip install -r "%REQ_FILE%" -c "%KNOWN_GOOD_FILE%"
) else (
  .venv\Scripts\python.exe -m pip install -r "%REQ_FILE%"
)
if errorlevel 1 (
  popd
  exit /b 1
)

echo Done. Activate with: .venv\Scripts\activate
popd
