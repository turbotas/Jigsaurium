@echo off
setlocal EnableDelayedExpansion

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

echo Python package update status:
set "PIP_OUTDATED_FILE=%TEMP%\jigsaurium_pip_outdated_%RANDOM%_%RANDOM%.txt"
%PYTHON_CMD% -m pip list --outdated > "%PIP_OUTDATED_FILE%"
set "UPDATES_EXIT=%ERRORLEVEL%"

for %%A in ("%PIP_OUTDATED_FILE%") do set "PIP_OUTDATED_SIZE=%%~zA"
if "!PIP_OUTDATED_SIZE!"=="0" (
  echo   All Python packages are up to date
) else (
  type "%PIP_OUTDATED_FILE%"
)
del "%PIP_OUTDATED_FILE%" >nul 2>&1

set "HAS_NPM=0"
where npm >nul 2>&1 && set "HAS_NPM=1"

if "%HAS_NPM%"=="1" (
  echo.
  echo GOV.UK frontend npm update status:
  set "GOVUK_PINNED="
  set "GOVUK_INSTALLED="
  set "GOVUK_LATEST="

  for /f "delims=" %%i in ('npm pkg get devDependencies.govuk-frontend --silent 2^>nul') do set "GOVUK_PINNED=%%i"
  for /f "delims=" %%i in ('node -p "try { require(\"./node_modules/govuk-frontend/package.json\").version || \"\" } catch (e) { \"\" }"') do set "GOVUK_INSTALLED=%%i"
  for /f "delims=" %%i in ('npm view govuk-frontend version --silent 2^>nul') do set "GOVUK_LATEST=%%i"

  set "GOVUK_PINNED=!GOVUK_PINNED:\"=!"
  set "GOVUK_PINNED=!GOVUK_PINNED:"=!"
  if "!GOVUK_PINNED!"=="{}" set "GOVUK_PINNED="

  if "!GOVUK_PINNED!"=="" (
    echo   Pinned   : not set in package.json
  ) else (
    echo   Pinned   : !GOVUK_PINNED!
  )

  if "!GOVUK_INSTALLED!"=="" (
    echo   Installed: not installed
  ) else (
    echo   Installed: !GOVUK_INSTALLED!
  )

  if "!GOVUK_LATEST!"=="" (
    echo   Latest   : unavailable
  ) else (
    echo   Latest   : !GOVUK_LATEST!
  )

  if not "!GOVUK_INSTALLED!"=="" if not "!GOVUK_LATEST!"=="" (
    if "!GOVUK_INSTALLED!"=="!GOVUK_LATEST!" (
      echo   Status   : up to date
    ) else (
      echo   Status   : update available
    )
  )
) else (
  echo.
  echo GOV.UK frontend npm update status: npm unavailable
)

popd
exit /b %UPDATES_EXIT%
