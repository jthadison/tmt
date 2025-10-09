"""
Historical Data API Endpoints

Provides REST API for querying historical market data, executions, and signals.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database import get_db_session
from ..repositories import HistoricalDataRepository
from ..models.market_data import (
    MarketCandleSchema,
    TradeExecutionSchema,
    TradingSignalSchema,
    DataQualityReport,
)
from ..services import DataQualityValidator

logger = structlog.get_logger()

router = APIRouter(prefix="/api/historical", tags=["historical-data"])


@router.get("/market-data")
async def get_market_data(
    instrument: str = Query(..., description="Trading instrument (e.g., EUR_USD)"),
    start_date: datetime = Query(..., description="Start date (ISO format)"),
    end_date: datetime = Query(..., description="End date (ISO format)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., H1, M15, D)"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve historical OHLCV market data

    Query 1 year of data in < 5 seconds (performance requirement)
    """
    try:
        logger.info(
            "API request: get_market_data",
            instrument=instrument,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            timeframe=timeframe,
        )

        repo = HistoricalDataRepository(session)
        df = await repo.get_market_data(instrument, start_date, end_date, timeframe)

        # Convert DataFrame to list of dicts for JSON response
        if df.empty:
            return {"data": [], "count": 0}

        data = df.reset_index().to_dict(orient="records")

        logger.info(f"Returning {len(data)} candles")

        return {"data": data, "count": len(data)}

    except Exception as e:
        logger.error("Error fetching market data", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions")
async def get_execution_history(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    instrument: Optional[str] = Query(None, description="Filter by instrument"),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Retrieve historical trade executions"""
    try:
        logger.info(
            "API request: get_execution_history",
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            instrument=instrument,
            account_id=account_id,
        )

        repo = HistoricalDataRepository(session)
        trades = await repo.get_execution_history(
            start_date, end_date, instrument, account_id
        )

        return {"trades": [t.dict() for t in trades], "count": len(trades)}

    except Exception as e:
        logger.error("Error fetching execution history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_signal_history(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Min confidence"),
    executed_only: bool = Query(False, description="Only executed signals"),
    instrument: Optional[str] = Query(None, description="Filter by instrument"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Retrieve historical trading signals"""
    try:
        logger.info(
            "API request: get_signal_history",
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            min_confidence=min_confidence,
            executed_only=executed_only,
        )

        repo = HistoricalDataRepository(session)
        signals = await repo.get_signal_history(
            start_date, end_date, min_confidence, executed_only, instrument
        )

        return {"signals": [s.dict() for s in signals], "count": len(signals)}

    except Exception as e:
        logger.error("Error fetching signal history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{instrument}")
async def get_data_statistics(
    instrument: str,
    timeframe: str = Query("H1", description="Timeframe"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get data coverage statistics for an instrument"""
    try:
        logger.info(
            "API request: get_data_statistics",
            instrument=instrument,
            timeframe=timeframe,
        )

        repo = HistoricalDataRepository(session)
        stats = await repo.get_data_statistics(instrument, timeframe)

        return stats

    except Exception as e:
        logger.error("Error fetching data statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-quality")
async def validate_data_quality(
    instrument: str = Query(..., description="Instrument to validate"),
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    timeframe: str = Query("H1", description="Timeframe"),
    session: AsyncSession = Depends(get_db_session),
) -> DataQualityReport:
    """
    Validate data quality for specified date range

    Checks for gaps, outliers, and completeness.
    """
    try:
        logger.info(
            "API request: validate_data_quality",
            instrument=instrument,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )

        # Fetch candles from database
        repo = HistoricalDataRepository(session)
        df = await repo.get_market_data(instrument, start_date, end_date, timeframe)

        # Convert to candle schemas
        candles = [
            MarketCandleSchema(
                timestamp=row.Index,
                instrument=instrument,
                timeframe=timeframe,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in df.itertuples()
        ]

        # Validate quality
        validator = DataQualityValidator()
        report = validator.validate_candles(
            candles, instrument, start_date, end_date, timeframe
        )

        return report

    except Exception as e:
        logger.error("Error validating data quality", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backtesting-historical-data",
        "version": "1.0.0",
    }
