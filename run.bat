@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not "%~1"=="" (
    uv run python -m agent_project %*
    exit /b %ERRORLEVEL%
)

echo Usage: run.bat [-v] "your goal" [--image /data/file.png]
echo Later goals keep the same agent context. Ctrl+C exits.
echo Example: run.bat -v "What is on my agenda tonight?"
echo.
set /p GOAL=Goal: 
if "%GOAL%"=="" (
    echo No goal given.
    exit /b 1
)

uv run python -m agent_project "%GOAL%"
exit /b %ERRORLEVEL%
