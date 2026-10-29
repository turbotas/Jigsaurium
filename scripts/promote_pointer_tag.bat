@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul 2>&1 || (
  echo ERROR: Failed to access repository root from script path.
  exit /b 1
)

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage

set "OWNER=%~1"
set "POINTER=%~2"
set "SOURCE_REF=%~3"
set "IMAGE_NAME=jigsaurium"
if not "%~4"=="" set "IMAGE_NAME=%~4"

powershell -NoProfile -Command "$o='%OWNER%'; if($o -match '^[A-Za-z0-9](?:-?[A-Za-z0-9])*$'){ exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo ERROR: owner "%OWNER%" is not a valid GitHub owner name.
  echo        Use your GitHub username or organization, not a domain name.
  popd
  exit /b 1
)

if /I not "%POINTER%"=="dev" if /I not "%POINTER%"=="test" if /I not "%POINTER%"=="prod" (
  echo ERROR: pointer must be one of: dev, test, prod
  popd
  exit /b 1
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "'%OWNER%'.ToLowerInvariant()"') do set "OWNER_LOWER=%%i"
if not defined OWNER_LOWER (
  echo ERROR: Unable to normalize owner name.
  popd
  exit /b 1
)
set "IMAGE=ghcr.io/%OWNER_LOWER%/%IMAGE_NAME%"

echo %SOURCE_REF% | findstr /B /C:"sha256:" >nul
if errorlevel 1 (
  set "SOURCE_IMAGE=%IMAGE%:%SOURCE_REF%"
) else (
  set "SOURCE_IMAGE=%IMAGE%@%SOURCE_REF%"
)

echo Promoting %SOURCE_IMAGE% ^> %IMAGE%:%POINTER%

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

docker buildx imagetools create -t %IMAGE%:%POINTER% %SOURCE_IMAGE%
if errorlevel 1 (
  echo ERROR: pointer promotion failed.
  popd
  exit /b 1
)

echo Promotion completed: %IMAGE%:%POINTER%
popd
exit /b 0

:usage
echo Usage: scripts\promote_pointer_tag.bat ^<owner^> ^<pointer^> ^<source_ref^> [image_name]
echo Example: scripts\promote_pointer_tag.bat my-github-org test v0.1.0
echo Example: scripts\promote_pointer_tag.bat my-github-org prod sha256:abc123...
popd
exit /b 1
