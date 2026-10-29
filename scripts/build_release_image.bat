@echo off
setlocal EnableExtensions EnableDelayedExpansion

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "VERSION=%~1"
set "OWNER=%~2"
set "IMAGE_NAME=jigsaurium"
if not "%~3"=="" set "IMAGE_NAME=%~3"

echo %VERSION% | findstr /R "^v[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo ERROR: VERSION must match SemVer tag format, e.g. v1.2.3
  exit /b 1
)

for /f "delims=" %%i in ('git rev-parse --short=12 HEAD') do set "SHORT_SHA=%%i"
for /f "delims=" %%i in ('git rev-parse HEAD') do set "FULL_SHA=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')"') do set "BUILD_TIME=%%i"

set "OWNER_LOWER=%OWNER%"
for %%A in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do call set "OWNER_LOWER=%%OWNER_LOWER:%%A=%%a%%"

set "IMAGE=ghcr.io/%OWNER_LOWER%/%IMAGE_NAME%"

echo.
echo Building %IMAGE%:%VERSION%
echo Commit  : %FULL_SHA%
echo Built at: %BUILD_TIME%
echo.

docker login ghcr.io
if errorlevel 1 (
  echo ERROR: docker login failed.
  exit /b 1
)

docker buildx build --platform linux/amd64 --build-arg APP_VERSION=%VERSION% --build-arg APP_BUILD_SHA=%FULL_SHA% --build-arg APP_BUILD_TIME=%BUILD_TIME% -t %IMAGE%:%VERSION% -t %IMAGE%:sha-%SHORT_SHA% --push .
if errorlevel 1 (
  echo ERROR: docker buildx build failed.
  exit /b 1
)

echo.
echo Release image pushed: %IMAGE%:%VERSION%
echo SHA tag pushed      : %IMAGE%:sha-%SHORT_SHA%
exit /b 0

:usage
echo Usage: scripts\build_release_image.bat ^<version^> ^<owner^> [image_name]
echo Example: scripts\build_release_image.bat v0.1.0 my-github-org
exit /b 1
