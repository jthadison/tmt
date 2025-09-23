@echo off
echo 🚀 Starting TMT Trading System in Docker...

REM Check if .env.docker exists
if not exist .env.docker (
    echo ❌ .env.docker file not found!
    echo Please copy .env.docker to configure your OANDA API credentials
    exit /b 1
)

echo 📋 Configuration loaded from .env.docker

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM Build and start core services
echo 🏗️  Building and starting core services...
docker-compose -f docker-compose.current.yml --env-file .env.docker up --build -d orchestrator market-analysis execution-engine dashboard

REM Wait for services to be healthy
echo ⏳ Waiting for services to be healthy...
timeout 10 >nul

REM Check service health
echo 🔍 Checking service health...

curl -f http://localhost:8089/health >nul 2>&1
if errorlevel 1 (
    echo   ❌ Orchestrator ^(port 8089^) - not responding
) else (
    echo   ✅ Orchestrator ^(port 8089^) - healthy
)

curl -f http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo   ❌ Market Analysis ^(port 8001^) - not responding
) else (
    echo   ✅ Market Analysis ^(port 8001^) - healthy
)

curl -f http://localhost:8082/health >nul 2>&1
if errorlevel 1 (
    echo   ❌ Execution Engine ^(port 8082^) - not responding
) else (
    echo   ✅ Execution Engine ^(port 8082^) - healthy
)

curl -f http://localhost:3000 >nul 2>&1
if errorlevel 1 (
    echo   ❌ Dashboard ^(port 3000^) - not responding
) else (
    echo   ✅ Dashboard ^(port 3000^) - healthy
)

echo.
echo 🎯 Trading System is running!
echo 📊 Dashboard: http://localhost:3000
echo 🤖 Orchestrator: http://localhost:8089/health
echo 📈 Market Analysis: http://localhost:8001/health
echo ⚡ Execution Engine: http://localhost:8082/health
echo.
echo To start all AI agents:
echo   docker-compose -f docker-compose.current.yml up -d
echo.
echo To stop the system:
echo   docker-compose -f docker-compose.current.yml down
echo.
echo To view logs:
echo   docker-compose -f docker-compose.current.yml logs -f [service-name]