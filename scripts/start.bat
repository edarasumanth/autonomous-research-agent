@echo off
REM =============================================================================
REM Research Agent - Windows Startup Script
REM =============================================================================

echo.
echo ========================================
echo   Autonomous Research Agent
echo ========================================
echo.

REM Check if running with Docker or locally
if "%1"=="docker" goto docker_start
if "%1"=="local" goto local_start
goto show_usage

:docker_start
echo Starting with Docker...
docker-compose up -d
echo.
echo Application started at: http://localhost:8501
echo.
echo Commands:
echo   - View logs:  docker-compose logs -f
echo   - Stop:       docker-compose down
echo.
goto end

:local_start
echo Starting locally...
cd /d "%~dp0.."
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)
echo.
echo Starting Streamlit server...
streamlit run streamlit_app.py
goto end

:show_usage
echo Usage: start.bat [docker^|local]
echo.
echo   docker  - Start using Docker (recommended for production)
echo   local   - Start using local Python environment
echo.

:end
