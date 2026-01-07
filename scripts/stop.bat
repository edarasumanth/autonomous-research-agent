@echo off
REM =============================================================================
REM Research Agent - Windows Stop Script
REM =============================================================================

echo.
echo Stopping Research Agent...
echo.

if "%1"=="docker" goto docker_stop
if "%1"=="local" goto local_stop
goto show_usage

:docker_stop
echo Stopping Docker containers...
docker-compose down
echo Done.
goto end

:local_stop
echo Stopping local Streamlit process...
taskkill /F /IM streamlit.exe 2>nul
if %errorlevel%==0 (
    echo Streamlit stopped.
) else (
    echo No Streamlit process found.
)
goto end

:show_usage
echo Usage: stop.bat [docker^|local]
echo.
echo   docker  - Stop Docker containers
echo   local   - Stop local Streamlit process
echo.

:end
