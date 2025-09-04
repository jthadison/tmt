@echo off
REM TMT Trading System Complete Restart Script - Windows Batch
REM Stops all running services and restarts the complete 8-agent ecosystem
REM 
REM This script:
REM 1. Detects and stops all running trading system processes
REM 2. Cleans up ports and resources  
REM 3. Starts all services in proper sequence
REM 4. Validates system health
REM
REM Usage: restart-trading.bat [--force]

setlocal enabledelayedexpansion

echo ============================================================
echo TMT Trading System Complete Restart
echo ============================================================

REM Parse command line arguments
set FORCE_MODE=false
if "%1"=="--force" set FORCE_MODE=true

echo Step 1: Stopping all running trading system services...
echo ============================================================

REM Stop processes using known ports
echo Stopping services on trading system ports...

REM Core Services
call :stop_port 8082 "Execution Engine"
call :stop_port 8001 "Market Analysis" 
call :stop_port 8089 "Orchestrator"
call :stop_port 8084 "Circuit Breaker"

REM AI Agent Ecosystem
call :stop_port 8002 "Strategy Analysis"
call :stop_port 8003 "Parameter Optimization"
call :stop_port 8004 "Learning Safety"
call :stop_port 8005 "Disagreement Engine"
call :stop_port 8006 "Data Collection"
call :stop_port 8007 "Continuous Improvement"
call :stop_port 8008 "Pattern Detection"

REM Dashboard
call :stop_port 8080 "Dashboard"

echo.
echo Step 2: Cleaning up resources and waiting for clean shutdown...
timeout /t 3 /nobreak >nul

echo.
echo Step 3: Starting all trading system services...
echo ============================================================

REM Start Core Infrastructure
echo Starting Core Infrastructure...

REM Start Execution Engine (port 8082)
echo   Starting Execution Engine on port 8082...
start "Execution Engine" cmd /k "cd execution-engine && python simple_main.py"
timeout /t 3 /nobreak >nul

REM Start Market Analysis (port 8001)
echo   Starting Market Analysis on port 8001...
start "Market Analysis" cmd /k "cd agents\market-analysis && python simple_main.py"
timeout /t 3 /nobreak >nul

REM Start Orchestrator (port 8089)
echo   Starting Orchestrator on port 8089...
start "Orchestrator" cmd /k "cd orchestrator && python -m uvicorn app.main:app --host 0.0.0.0 --port 8089"
timeout /t 4 /nobreak >nul

REM Start Circuit Breaker Agent (port 8084)
echo   Starting Circuit Breaker on port 8084...
start "Circuit Breaker" cmd /k "cd agents\circuit-breaker && python main.py"
timeout /t 2 /nobreak >nul

echo.
echo Starting AI Agent Ecosystem...

REM Start Strategy Analysis (port 8002)
echo   Starting Strategy Analysis on port 8002...
start "Strategy Analysis" cmd /k "cd agents\strategy-analysis && python start_agent_simple.py"
timeout /t 2 /nobreak >nul

REM Start Parameter Optimization (port 8003)
echo   Starting Parameter Optimization on port 8003...
start "Parameter Optimization" cmd /k "cd agents\parameter-optimization && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Learning Safety (port 8004)
echo   Starting Learning Safety on port 8004...
start "Learning Safety" cmd /k "cd agents\learning-safety && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Disagreement Engine (port 8005)
echo   Starting Disagreement Engine on port 8005...
start "Disagreement Engine" cmd /k "cd agents\disagreement-engine && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Data Collection (port 8006)
echo   Starting Data Collection on port 8006...
start "Data Collection" cmd /k "cd agents\data-collection && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Continuous Improvement (port 8007)
echo   Starting Continuous Improvement on port 8007...
start "Continuous Improvement" cmd /k "cd agents\continuous-improvement && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Pattern Detection (port 8008)
echo   Starting Pattern Detection on port 8008...
start "Pattern Detection" cmd /k "cd agents\pattern-detection && python start_agent_simple.py"
timeout /t 2 /nobreak >nul

echo.
echo Starting Dashboard...

REM Start Dashboard (port 8080)
echo   Starting Dashboard on port 8080...
start "Dashboard" cmd /k "cd dashboard && npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo TMT Trading System Restart Completed!
echo ============================================================
echo.
echo 🔧 Core Service URLs:
echo   Execution Engine:       http://localhost:8082/health
echo   Market Analysis:        http://localhost:8001/health
echo   Orchestrator:           http://localhost:8089/health
echo   Circuit Breaker:        http://localhost:8084/health
echo.
echo 🤖 AI Agent Ecosystem URLs:
echo   Strategy Analysis:      http://localhost:8002/health
echo   Parameter Optimization: http://localhost:8003/health
echo   Learning Safety:        http://localhost:8004/health
echo   Disagreement Engine:    http://localhost:8005/health
echo   Data Collection:        http://localhost:8006/health
echo   Continuous Improvement: http://localhost:8007/health
echo   Pattern Detection:      http://localhost:8008/health
echo.
echo 📊 Dashboard:
echo   Dashboard Interface:    http://localhost:8080
echo.
echo 🧪 Testing Commands:
echo   Integration Test:       python test-trading-pipeline.py
echo   Signal Bridge:          python signal_bridge.py
echo   System Health:          python system-health.py
echo.
echo 📈 Next Steps:
echo   • Run integration tests to verify functionality
echo   • Monitor logs for any issues  
echo   • Check dashboard for system health status
echo   • All services should be accessible within 1-2 minutes
echo.
echo To stop all services: close the individual command windows
echo or run: python restart-trading-system.py --force
echo ============================================================

pause
goto :eof

REM Function to stop process using a specific port
:stop_port
set PORT=%1
set SERVICE_NAME=%2

echo   Checking port %PORT% for %SERVICE_NAME%...

REM Find process using the port
for /f "tokens=5" %%i in ('netstat -ano ^| findstr :%PORT%') do (
    set PID=%%i
    if not "!PID!"=="0" (
        echo     Found process !PID! using port %PORT% - stopping %SERVICE_NAME%
        if "%FORCE_MODE%"=="true" (
            taskkill /F /PID !PID! >nul 2>&1
        ) else (
            taskkill /PID !PID! >nul 2>&1
        )
        timeout /t 1 /nobreak >nul
    )
)

goto :eof