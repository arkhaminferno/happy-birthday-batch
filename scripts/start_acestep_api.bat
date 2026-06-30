@echo off
REM Start ACE-Step API (Windows + NVIDIA CUDA). Run in a dedicated terminal.
setlocal
set "ROOT=%~dp0.."
if defined ACESTEP_ROOT (
  set "ACESTEP_DIR=%ACESTEP_ROOT%"
) else (
  set "ACESTEP_DIR=%ROOT%\..\ACE-Step-1.5"
)
if not exist "%ACESTEP_DIR%\acestep" (
  echo ACE-Step not found at: %ACESTEP_DIR%
  echo Set ACESTEP_ROOT or clone ACE-Step-1.5 next to this repo.
  exit /b 1
)
set ACESTEP_INIT_LLM=true
cd /d "%ACESTEP_DIR%"
if exist "%ACESTEP_DIR%\start_api_server.bat" (
  call "%ACESTEP_DIR%\start_api_server.bat"
) else (
  echo Missing start_api_server.bat in %ACESTEP_DIR%
  exit /b 1
)
