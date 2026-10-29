@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul 2>&1 || (
  echo ERROR: Failed to access repository root from script path.
  exit /b 1
)

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "VERSION=%~1"
set "OWNER=%~2"
set "IMAGE_NAME=jigsaurium"
if not "%~3"=="" set "IMAGE_NAME=%~3"

powershell -NoProfile -Command "$v='%VERSION%'; if($v -match '^v\d+\.\d+\.\d+$'){ exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo ERROR: VERSION must match SemVer tag format, e.g. v1.2.3
  popd
  exit /b 1
)

if "%OWNER%"=="" (
  echo ERROR: owner must be a GitHub username or organization.
  popd
  exit /b 1
)

powershell -NoProfile -Command "$o='%OWNER%'; if($o -match '^[A-Za-z0-9](?:-?[A-Za-z0-9])*$'){ exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo ERROR: owner "%OWNER%" is not a valid GitHub owner name.
  echo        Use your GitHub username or organization, not a domain name.
  popd
  exit /b 1
)

for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set "FULL_SHA=%%i"
if not defined FULL_SHA (
  echo ERROR: Unable to resolve git commit SHA. Are you running inside the repo?
  popd
  exit /b 1
)

set "SHORT_SHA=%FULL_SHA:~0,12%"
if not defined SHORT_SHA (
  echo ERROR: Unable to derive short commit SHA.
  popd
  exit /b 1
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')"') do set "BUILD_TIME=%%i"

for /f "delims=" %%i in ('powershell -NoProfile -Command "'%OWNER%'.ToLowerInvariant()"') do set "OWNER_LOWER=%%i"
if not defined OWNER_LOWER (
  echo ERROR: Unable to normalize owner name.
  popd
  exit /b 1
)

set "IMAGE=ghcr.io/%OWNER_LOWER%/%IMAGE_NAME%"

echo.
echo Building %IMAGE%:%VERSION%
echo Commit  : %FULL_SHA%
echo Built at: %BUILD_TIME%
echo.

if /I "%GHCR_SKIP_LOGIN%"=="1" (
  echo Skipping docker login because GHCR_SKIP_LOGIN=1.
) else if defined GHCR_TOKEN (
  set "LOGIN_USER=%GHCR_USERNAME%"
  if "%LOGIN_USER%"=="" set "LOGIN_USER=%OWNER%"
  powershell -NoProfile -Command "$env:GHCR_TOKEN" | docker login ghcr.io -u "%LOGIN_USER%" --password-stdin
  if errorlevel 1 (
    echo ERROR: docker login failed.
    popd
    exit /b 1
  )
) else (
  echo GHCR_TOKEN not set. Using existing Docker credential store session for ghcr.io.
)

docker buildx build --platform linux/amd64 --build-arg APP_VERSION=%VERSION% --build-arg APP_BUILD_SHA=%FULL_SHA% --build-arg APP_BUILD_TIME=%BUILD_TIME% -t %IMAGE%:%VERSION% -t %IMAGE%:sha-%SHORT_SHA% --push .
if errorlevel 1 (
  echo ERROR: docker buildx build failed.
  popd
  exit /b 1
)

echo.
echo Release image pushed: %IMAGE%:%VERSION%
echo SHA tag pushed      : %IMAGE%:sha-%SHORT_SHA%
popd
exit /b 0

:usage
echo Usage: scripts\build_release_image.bat ^<version^> ^<owner^> [image_name]
echo Example: scripts\build_release_image.bat v0.1.0 my-github-org
echo Note: owner must be a GitHub username or organization (not a domain).
popd
exit /b 1
