"""API endpoints for backtesting service"""

from .historical_data import router as historical_data_router

__all__ = ["historical_data_router"]
