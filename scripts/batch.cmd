@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
where celebratevibes >nul 2>&1
if %ERRORLEVEL%==0 (
  celebratevibes %*
  exit /b %ERRORLEVEL%
)
where uv >nul 2>&1
if %ERRORLEVEL%==0 (
  uv run celebratevibes %*
  exit /b %ERRORLEVEL%
)
python cli_entry.py %*
exit /b %ERRORLEVEL%
