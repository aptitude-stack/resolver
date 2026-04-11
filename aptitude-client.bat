@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
set "PYTHONPATH=%ROOT_DIR%src;%PYTHONPATH%"

where py >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python launcher "py" was not found on PATH.
    echo Install Python 3 and make sure the "py" launcher is available.
    exit /b 1
)

py -3 -c "import httpx, packaging, pydantic, pydantic_settings, typer" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Required Python packages are missing.
    echo Run ".\aptitude-dev.bat setup" once, or install the project dependencies manually.
    exit /b 1
)

if "%~1"=="" (
    echo Aptitude Client interactive shell
    echo Type client commands such as:
    echo   resolve "python lint"
    echo   install "python lint" --target skill_demo
    echo Type help to show CLI help, or exit to quit.
    echo.
    goto :interactive
)

py -3 -m aptitude_client.interfaces.cli.main %*
exit /b %ERRORLEVEL%

:interactive
set "CLI_INPUT="
set /p CLI_INPUT=aptitude^> 

if "%CLI_INPUT%"=="" goto :interactive
if /I "%CLI_INPUT%"=="exit" exit /b 0
if /I "%CLI_INPUT%"=="quit" exit /b 0
if /I "%CLI_INPUT%"=="help" (
    py -3 -m aptitude_client.interfaces.cli.main --help
    echo.
    goto :interactive
)

call py -3 -m aptitude_client.interfaces.cli.main %CLI_INPUT%
echo.
goto :interactive
