"""
Backtest REST API Endpoints - Story 11.2

Provides REST API for running backtests:
- POST /api/backtest/run - Run a backtest
- GET /api/backtest/{backtest_id} - Get backtest results
- POST /api/backtest/compare - Compare multiple parameter sets
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import uuid
import logging

from ..backtesting.models import BacktestConfig, BacktestResult
from ..backtesting.engine import BacktestEngine
from ..repositories.historical_data_repository import HistoricalDataRepository
from ..database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtesting"])


# In-memory cache for backtest results (production would use Redis/database)
_backtest_results_cache: Dict[str, BacktestResult] = {}


@router.post("/run", response_model=Dict)
async def run_backtest(
    config: BacktestConfig,
    session=Depends(get_db_session)
):
    """
    Run a backtest with given configuration

    This endpoint:
    1. Validates configuration
    2. Loads historical market data from TimescaleDB
    3. Runs backtest with specified parameters
    4. Returns comprehensive performance metrics

    **Performance**: 1-year backtest completes in < 2 minutes

    **Request Body**:
    ```json
    {
      "start_date": "2023-01-01T00:00:00Z",
      "end_date": "2024-01-01T00:00:00Z",
      "instruments": ["EUR_USD", "GBP_USD"],
      "initial_capital": 100000.0,
      "risk_percentage": 0.02,
      "parameters": {
        "confidence_threshold": 55.0,
        "min_risk_reward": 1.8
      },
      "slippage_model": "session_based",
      "timeframe": "H1"
    }
    ```

    **Response**:
    - Returns backtest_id for retrieving results
    - Includes execution summary

    **Errors**:
    - 400: Invalid configuration
    - 404: Market data not found for requested period
    - 500: Backtest execution error
    """

    try:
        logger.info(f"Backtest requested: {len(config.instruments)} instruments")

        # Generate backtest ID
        backtest_id = str(uuid.uuid4())

        # Load historical market data
        repo = HistoricalDataRepository(session)

        market_data = {}

        for instrument in config.instruments:
            logger.info(f"Loading data for {instrument}...")

            df = await repo.get_market_data(
                instrument=instrument,
                start_date=config.start_date,
                end_date=config.end_date,
                timeframe=config.timeframe
            )

            if df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No market data found for {instrument} in specified period"
                )

            market_data[instrument] = df
            logger.info(f"{instrument}: {len(df)} candles loaded")

        # Create backtest engine
        engine = BacktestEngine(config, enable_validation=True)

        # Run backtest
        logger.info("Starting backtest execution...")
        result = await engine.run(market_data)

        # Cache results
        _backtest_results_cache[backtest_id] = result

        logger.info(f"Backtest completed: {backtest_id}")

        # Return summary (full results available via GET endpoint)
        return {
            "backtest_id": backtest_id,
            "status": "completed",
            "summary": {
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "total_return_pct": result.total_return_pct,
                "cagr": result.cagr,
                "max_drawdown_pct": result.max_drawdown_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "profit_factor": result.profit_factor,
                "execution_time_seconds": result.execution_time_seconds
            },
            "message": f"Backtest completed in {result.execution_time_seconds:.1f}s"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Backtest execution failed: {str(e)}"
        )


@router.get("/{backtest_id}", response_model=BacktestResult)
async def get_backtest_results(backtest_id: str):
    """
    Retrieve complete backtest results

    Returns full BacktestResult including:
    - All performance metrics
    - Complete trade list
    - Equity curve
    - Per-session breakdown
    - Per-instrument breakdown

    **Parameters**:
    - `backtest_id`: Backtest ID from /run endpoint

    **Response**: Complete BacktestResult model

    **Errors**:
    - 404: Backtest ID not found
    """

    if backtest_id not in _backtest_results_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {backtest_id} not found"
        )

    result = _backtest_results_cache[backtest_id]

    return result


@router.post("/compare", response_model=Dict)
async def compare_parameter_sets(
    base_config: BacktestConfig,
    parameter_sets: List[Dict],
    session=Depends(get_db_session)
):
    """
    Run parallel backtests with multiple parameter sets

    Useful for parameter optimization and comparison.

    Runs backtests in parallel (up to 10 concurrent) for performance.

    **Request Body**:
    ```json
    {
      "base_config": {
        "start_date": "2023-01-01T00:00:00Z",
        "end_date": "2024-01-01T00:00:00Z",
        "instruments": ["EUR_USD"],
        "initial_capital": 100000.0,
        "parameters": {}
      },
      "parameter_sets": [
        {
          "name": "Conservative",
          "parameters": {
            "confidence_threshold": 70.0,
            "min_risk_reward": 2.5
          }
        },
        {
          "name": "Aggressive",
          "parameters": {
            "confidence_threshold": 55.0,
            "min_risk_reward": 1.8
          }
        }
      ]
    }
    ```

    **Response**: Comparison of all parameter sets with key metrics

    **Errors**:
    - 400: Invalid configuration
    - 500: Execution error
    """

    try:
        if len(parameter_sets) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 parameter sets allowed for comparison"
            )

        logger.info(f"Parameter comparison: {len(parameter_sets)} sets")

        # Load market data once (shared across all backtests)
        repo = HistoricalDataRepository(session)

        market_data = {}

        for instrument in base_config.instruments:
            df = await repo.get_market_data(
                instrument=instrument,
                start_date=base_config.start_date,
                end_date=base_config.end_date,
                timeframe=base_config.timeframe
            )

            if df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No market data found for {instrument}"
                )

            market_data[instrument] = df

        # Run backtests in parallel
        tasks = []

        for param_set in parameter_sets:
            # Create config for this parameter set
            config = base_config.model_copy(deep=True)
            config.parameters.update(param_set.get('parameters', {}))

            # Create engine and run
            engine = BacktestEngine(config, enable_validation=False)  # Disable validation for speed
            task = engine.run(market_data)
            tasks.append(task)

        # Execute all backtests in parallel
        logger.info("Running parallel backtests...")
        results = await asyncio.gather(*tasks)

        # Build comparison
        comparison = {
            'parameter_sets': [],
            'best_sharpe': None,
            'best_cagr': None,
            'best_win_rate': None,
            'execution_time_total': sum(r.execution_time_seconds for r in results)
        }

        best_sharpe_idx = max(range(len(results)), key=lambda i: results[i].sharpe_ratio)
        best_cagr_idx = max(range(len(results)), key=lambda i: results[i].cagr)
        best_wr_idx = max(range(len(results)), key=lambda i: results[i].win_rate)

        for idx, (param_set, result) in enumerate(zip(parameter_sets, results)):
            comparison['parameter_sets'].append({
                'name': param_set.get('name', f'Set {idx + 1}'),
                'parameters': param_set.get('parameters'),
                'metrics': {
                    'total_trades': result.total_trades,
                    'win_rate': result.win_rate,
                    'cagr': result.cagr,
                    'max_drawdown_pct': result.max_drawdown_pct,
                    'sharpe_ratio': result.sharpe_ratio,
                    'profit_factor': result.profit_factor,
                    'total_return_pct': result.total_return_pct
                },
                'is_best_sharpe': idx == best_sharpe_idx,
                'is_best_cagr': idx == best_cagr_idx,
                'is_best_win_rate': idx == best_wr_idx
            })

        comparison['best_sharpe'] = parameter_sets[best_sharpe_idx].get('name')
        comparison['best_cagr'] = parameter_sets[best_cagr_idx].get('name')
        comparison['best_win_rate'] = parameter_sets[best_wr_idx].get('name')

        logger.info(f"Parameter comparison completed: {len(parameter_sets)} sets")

        return comparison

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parameter comparison error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Parameter comparison failed: {str(e)}"
        )


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """
    Delete cached backtest results

    **Parameters**:
    - `backtest_id`: Backtest ID to delete

    **Response**: Confirmation message

    **Errors**:
    - 404: Backtest ID not found
    """

    if backtest_id not in _backtest_results_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {backtest_id} not found"
        )

    del _backtest_results_cache[backtest_id]

    return {"message": f"Backtest {backtest_id} deleted"}


@router.get("/")
async def list_backtests():
    """
    List all cached backtests

    **Response**: List of backtest IDs with summary info
    """

    backtests = []

    for backtest_id, result in _backtest_results_cache.items():
        backtests.append({
            'backtest_id': backtest_id,
            'instruments': result.config.instruments,
            'date_range': {
                'start': result.config.start_date.isoformat(),
                'end': result.config.end_date.isoformat()
            },
            'total_trades': result.total_trades,
            'win_rate': result.win_rate,
            'cagr': result.cagr,
            'execution_time': result.execution_time_seconds
        })

    return {
        'total_backtests': len(backtests),
        'backtests': backtests
    }
