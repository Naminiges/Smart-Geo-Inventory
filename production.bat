@echo off
REM Smart Geo Inventory - Production Start Script for Windows
REM This script starts the application with Gunicorn production server

REM Set environment variables
set FLASK_ENV=production
set FLASK_DEBUG=0

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please create .env file with production configuration
    exit /b 1
)

REM Start with Gunicorn using threaded configuration
echo Starting Smart Geo Inventory with Gunicorn...
echo Configuration: gunicorn_threaded.conf.py
echo.

REM Start Gunicorn (if installed) or fallback to waitres
REM Note: Gunicorn on Windows requires special setup or use Waitress as alternative
where gunicorn >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    gunicorn -c gunicorn_threaded.conf.py run:app
) else (
    echo Gunicorn not found. Installing waitress as alternative...
    pip install waitress
    echo.
    echo Starting with Waitress (Windows-compatible WSGI server)...
    waitress-serve --listen=0.0.0.0:5000 --threads=4 run:app
)

pause
