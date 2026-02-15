@echo off
REM MonadSus Production Launch Script
REM Quick start for production deployment

echo ========================================
echo   MonadSus Production Launch
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Testing imports...
python -c "import blockchain; import tokenization; import openclaw_agent" 2>nul
if errorlevel 1 (
    echo [ERROR] Import test failed
    pause
    exit /b 1
)

echo [3/4] Starting trading server...
start "MonadSus Trading Server" python trading_server.py

REM Wait for server to start
timeout /t 3 /nobreak >nul

echo [4/4] Starting game...
echo.
echo ========================================
echo   Game Starting!
echo ========================================
echo.
echo Trading UI: http://localhost:8000
echo.
echo Press Ctrl+C to stop the game
echo ========================================
echo.

python main_autonomous.py

echo.
echo Game stopped.
pause
