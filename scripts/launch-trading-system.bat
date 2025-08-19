@echo off
REM ############################################################################
REM Trading System Launcher for Windows
REM Full system startup with health checks and OANDA integration
REM ############################################################################

setlocal enabledelayedexpansion

REM Colors for output (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Configuration
set "PROJECT_ROOT=%~dp0.."
set "COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"
set "ENV_FILE=%PROJECT_ROOT%\.env"
set "PYTHON_CMD="

echo %BLUE%🚀 Trading System Launcher v1.0 (Windows)%NC%
echo ==================================

REM Check for Python
echo %BLUE%🔍 Checking for Python...%NC%
where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    echo %GREEN%✅ Found Python in PATH%NC%
) else (
    if exist "C:\Python313\python.exe" (
        set "PYTHON_CMD=C:\Python313\python.exe"
        echo %GREEN%✅ Found Python at C:\Python313%NC%
    ) else (
        echo %YELLOW%⚠️  Python not found. Some features will be disabled.%NC%
    )
)

REM Check if Docker is running
echo %BLUE%🔍 Checking Docker status...%NC%
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Docker is not running. Please start Docker Desktop.%NC%
    pause
    exit /b 1
)
echo %GREEN%✅ Docker is running%NC%

REM Parse command line arguments
set "MODE=%1"
if "%MODE%"=="" set "MODE=default"

if "%MODE%"=="--stop" (
    echo %YELLOW%⚠️  Shutting down trading system...%NC%
    docker-compose -f "%COMPOSE_FILE%" down
    echo %GREEN%✅ System stopped%NC%
    pause
    exit /b 0
)

if "%MODE%"=="--status" (
    echo %BLUE%📋 System Status:%NC%
    echo ==================================
    docker-compose -f "%COMPOSE_FILE%" ps
    pause
    exit /b 0
)

REM Create .env file if it doesn't exist
if not exist "%ENV_FILE%" (
    if exist "%ENV_FILE%.example" (
        echo %YELLOW%📝 Creating .env file from template...%NC%
        copy "%ENV_FILE%.example" "%ENV_FILE%" >nul
        echo %YELLOW%⚠️  Please edit .env file with your OANDA credentials%NC%
        notepad "%ENV_FILE%"
        pause
    )
)

REM Clean up old containers
echo %BLUE%🧹 Cleaning up old containers...%NC%
docker-compose -f "%COMPOSE_FILE%" down --remove-orphans >nul 2>&1
echo %GREEN%✅ Cleanup complete%NC%

REM Launch infrastructure
echo %BLUE%🚀 Launching infrastructure services...%NC%
docker-compose -f "%COMPOSE_FILE%" up -d postgres redis kafka zookeeper vault

REM Wait for services
echo %YELLOW%⏳ Waiting for core services to be healthy...%NC%
timeout /t 10 /nobreak >nul

REM Check PostgreSQL
docker exec trading-postgres pg_isready -U postgres -d trading_system >nul 2>&1
if %errorlevel%==0 (
    echo %GREEN%✅ PostgreSQL ready%NC%
) else (
    echo %RED%❌ PostgreSQL not ready%NC%
)

REM Check Redis
docker exec trading-redis redis-cli ping >nul 2>&1
if %errorlevel%==0 (
    echo %GREEN%✅ Redis ready%NC%
) else (
    echo %RED%❌ Redis not ready%NC%
)

REM Launch monitoring if requested
if "%MODE%"=="--full" (
    echo %BLUE%📊 Launching monitoring services...%NC%
    docker-compose -f "%COMPOSE_FILE%" up -d prometheus grafana jaeger alertmanager
    echo %GREEN%✅ Monitoring stack launched%NC%
    
    echo %BLUE%🖥️  Launching dashboard...%NC%
    docker-compose -f "%COMPOSE_FILE%" up -d dashboard
    echo %GREEN%✅ Dashboard launched%NC%
)

if "%MODE%"=="--monitoring" (
    echo %BLUE%📊 Launching monitoring services...%NC%
    docker-compose -f "%COMPOSE_FILE%" up -d prometheus grafana jaeger alertmanager
    echo %GREEN%✅ Monitoring stack launched%NC%
)

REM Setup Kafka topics
echo %BLUE%📬 Setting up Kafka topics...%NC%
docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic market-data --partitions 3 --replication-factor 1 >nul 2>&1
docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic trading-signals --partitions 3 --replication-factor 1 >nul 2>&1
docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic trade-executions --partitions 3 --replication-factor 1 >nul 2>&1
docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic risk-events --partitions 1 --replication-factor 1 >nul 2>&1
docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic audit-logs --partitions 1 --replication-factor 1 >nul 2>&1
echo %GREEN%✅ Kafka topics ready%NC%

REM Test OANDA connectivity if Python is available
if not "%PYTHON_CMD%"=="" (
    if exist "%PROJECT_ROOT%\scripts\validate-oanda-connection.py" (
        echo %BLUE%🔌 Testing OANDA connectivity...%NC%
        "%PYTHON_CMD%" "%PROJECT_ROOT%\scripts\validate-oanda-connection.py"
    )
)

REM Display status
echo.
echo %GREEN%🎉 Trading System Successfully Launched!%NC%
echo ==================================
echo.
echo %BLUE%📌 Service URLs:%NC%
echo    Dashboard:     http://localhost:3000
echo    Grafana:       http://localhost:3001 (admin/admin)
echo    Jaeger UI:     http://localhost:16686
echo    Prometheus:    http://localhost:9090
echo    Alertmanager:  http://localhost:9094
echo.
echo %BLUE%📝 Commands:%NC%
echo    View logs:     docker-compose logs -f [service-name]
echo    Stop system:   launch-trading-system.bat --stop
echo    Status:        launch-trading-system.bat --status
echo.
echo %BLUE%🛑 To stop:%NC%
echo    Press Ctrl+C or run: launch-trading-system.bat --stop
echo.

pause