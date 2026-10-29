@echo off
setlocal EnableExtensions EnableDelayedExpansion

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage

set "OWNER=%~1"
set "POINTER=%~2"
set "SOURCE_REF=%~3"
set "IMAGE_NAME=jigsaurium"
if not "%~4"=="" set "IMAGE_NAME=%~4"

if /I not "%POINTER%"=="dev" if /I not "%POINTER%"=="test" if /I not "%POINTER%"=="prod" (
  echo ERROR: pointer must be one of: dev, test, prod
  exit /b 1
)

set "OWNER_LOWER=%OWNER%"
for %%A in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do call set "OWNER_LOWER=%%OWNER_LOWER:%%A=%%a%%"
set "IMAGE=ghcr.io/%OWNER_LOWER%/%IMAGE_NAME%"

echo %SOURCE_REF% | findstr /B /C:"sha256:" >nul
if errorlevel 1 (
  set "SOURCE_IMAGE=%IMAGE%:%SOURCE_REF%"
) else (
  set "SOURCE_IMAGE=%IMAGE%@%SOURCE_REF%"
)

echo Promoting %SOURCE_IMAGE% ^> %IMAGE%:%POINTER%

docker login ghcr.io
if errorlevel 1 (
  echo ERROR: docker login failed.
  exit /b 1
)

docker buildx imagetools create -t %IMAGE%:%POINTER% %SOURCE_IMAGE%
if errorlevel 1 (
  echo ERROR: pointer promotion failed.
  exit /b 1
)

echo Promotion completed: %IMAGE%:%POINTER%
exit /b 0

:usage
echo Usage: scripts\promote_pointer_tag.bat ^<owner^> ^<pointer^> ^<source_ref^> [image_name]
echo Example: scripts\promote_pointer_tag.bat my-github-org test v0.1.0
echo Example: scripts\promote_pointer_tag.bat my-github-org prod sha256:abc123...
exit /b 1
