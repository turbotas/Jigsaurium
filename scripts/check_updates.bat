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

rem First the venv against the reviewed lock (run.bat passes --no-python because it has already
rem checked and synced it), then what is newer than that on PyPI, and how each would arrive.
set "UPDATES_EXIT=0"
if /I not "%~1"=="--no-python" (
  %PYTHON_CMD% scripts\sync_dev_venv.py --profile dev
  echo.
)
%PYTHON_CMD% scripts\report_newer_releases.py --profile dev

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
