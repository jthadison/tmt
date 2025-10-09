"""
Backtesting & Historical Data Service

FastAPI application providing historical market data infrastructure
for backtesting, walk-forward optimization, and overfitting prevention.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
import logging

from .config import get_settings
from .database import db
from .api import historical_data_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()

    # Startup
    logger.info("Starting Backtesting & Historical Data Service")
    logger.info(f"Connecting to database: {settings.database_url}")

    # Initialize database connection
    await db.connect()

    # Create tables
    await db.create_tables()

    # Enable TimescaleDB (if not SQLite)
    if "postgresql" in settings.database_url:
        try:
            await db.enable_timescaledb()
        except Exception as e:
            logger.warning("Could not enable TimescaleDB", error=str(e))

    logger.info("Backtesting service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Backtesting service")
    await db.disconnect()
    logger.info("Backtesting service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Backtesting & Historical Data Service",
    description="Historical market data infrastructure for algorithmic validation",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(historical_data_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Backtesting & Historical Data Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "market_data": "/api/historical/market-data",
            "executions": "/api/historical/executions",
            "signals": "/api/historical/signals",
            "statistics": "/api/historical/statistics/{instrument}",
            "validate_quality": "/api/historical/validate-quality",
            "health": "/api/historical/health",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "backtesting-historical-data"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
