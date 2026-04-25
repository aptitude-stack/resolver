@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%scripts\list-server-artifact-formats.ps1" %*
exit /b %ERRORLEVEL%
