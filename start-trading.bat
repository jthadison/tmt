@echo off
REM Start Trading System - Windows Batch Script
REM Launches all core trading services

echo ============================================================
echo Starting TMT Trading System
echo ============================================================

REM Start Execution Engine (port 8082)
echo Starting Execution Engine on port 8082...
start "Execution Engine" cmd /k "cd execution-engine && python simple_main.py"
timeout /t 2 /nobreak >nul

REM Start Market Analysis (port 8001)
echo Starting Market Analysis on port 8001...
start "Market Analysis" cmd /k "cd agents\market-analysis && python simple_main.py"
timeout /t 2 /nobreak >nul

REM Start Orchestrator (port 8089)
echo Starting Orchestrator on port 8089...
start "Orchestrator" cmd /k "cd orchestrator && python -m uvicorn app.main:app --host 0.0.0.0 --port 8089"
timeout /t 3 /nobreak >nul

REM Start Circuit Breaker Agent (port 8086)
echo Starting Circuit Breaker on port 8086...
start "Circuit Breaker" cmd /k "cd agents\circuit-breaker && python main.py"
timeout /t 2 /nobreak >nul

REM Start AI Agent Ecosystem
echo Starting AI Agent Ecosystem...

REM Start Strategy Analysis (port 8002)
echo Starting Strategy Analysis on port 8002...
start "Strategy Analysis" cmd /k "cd agents\strategy-analysis && python start_agent_simple.py"
timeout /t 2 /nobreak >nul

REM Start Parameter Optimization (port 8003)
echo Starting Parameter Optimization on port 8003...
start "Parameter Optimization" cmd /k "cd agents\parameter-optimization && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Learning Safety (port 8004)
echo Starting Learning Safety on port 8004...
start "Learning Safety" cmd /k "cd agents\learning-safety && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Disagreement Engine (port 8005)
echo Starting Disagreement Engine on port 8005...
start "Disagreement Engine" cmd /k "cd agents\disagreement-engine && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Data Collection (port 8006)
echo Starting Data Collection on port 8006...
start "Data Collection" cmd /k "cd agents\data-collection && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Continuous Improvement (port 8007)
echo Starting Continuous Improvement on port 8007...
start "Continuous Improvement" cmd /k "cd agents\continuous-improvement && python start_agent.py"
timeout /t 2 /nobreak >nul

REM Start Pattern Detection (port 8008)
echo Starting Pattern Detection on port 8008...
start "Pattern Detection" cmd /k "cd agents\pattern-detection && python start_agent_simple.py"
timeout /t 2 /nobreak >nul

REM Start Dashboard (port 8080)
echo Starting Dashboard on port 8090...
start "Dashboard" cmd /k "cd dashboard && npm run dev"
timeout /t 3 /nobreak >nul

echo ============================================================
echo Trading System Started Successfully!
echo ============================================================
echo.
echo Core Service URLs:
echo   Execution Engine:     http://localhost:8082/health
echo   Market Analysis:      http://localhost:8001/health
echo   Orchestrator:         http://localhost:8089/health
echo   Circuit Breaker:      http://localhost:8086/health
echo.
echo AI Agent URLs:
echo   Strategy Analysis:    http://localhost:8002/health
echo   Parameter Optimization: http://localhost:8003/health
echo   Learning Safety:      http://localhost:8004/health
echo   Disagreement Engine:  http://localhost:8005/health
echo   Data Collection:      http://localhost:8006/health
echo   Continuous Improvement: http://localhost:8007/health
echo   Pattern Detection:    http://localhost:8008/health
echo.
echo Dashboard:              http://localhost:8090
echo.
echo To stop all services, close the individual command windows.
echo ============================================================
pause