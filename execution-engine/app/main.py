"""
Execution Engine MVP - Main API Application

High-performance execution engine with sub-100ms order placement.
Provides comprehensive order and position management with risk controls.
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.models import (
    Order,
    OrderRequest,
    OrderResult,
    Position,
    PositionCloseRequest,
    AccountSummary,
    RiskLimits,
)
from .orders.order_manager import OrderManager
from .positions.position_manager import PositionManager
from .risk.risk_manager import RiskManager
from .integrations.oanda_client import OandaExecutionClient, OandaConfig
from .monitoring.metrics import ExecutionMetricsCollector

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class ExecutionEngineState:
    """Global application state."""
    
    def __init__(self):
        self.oanda_client: Optional[OandaExecutionClient] = None
        self.order_manager: Optional[OrderManager] = None
        self.position_manager: Optional[PositionManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.metrics_collector: Optional[ExecutionMetricsCollector] = None
        self.initialized = False


# Global state
app_state = ExecutionEngineState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Execution Engine MVP")
    
    try:
        # Initialize OANDA client
        oanda_config = OandaConfig(
            api_key=os.getenv("OANDA_API_KEY", ""),
            account_id=os.getenv("OANDA_ACCOUNT_ID", ""),
            environment=os.getenv("OANDA_ENVIRONMENT", "practice"),
            timeout=float(os.getenv("OANDA_TIMEOUT", "5.0")),
            max_retries=int(os.getenv("OANDA_MAX_RETRIES", "3")),
            rate_limit_per_second=int(os.getenv("OANDA_RATE_LIMIT", "100")),
        )
        
        if not oanda_config.api_key or not oanda_config.account_id:
            logger.warning("OANDA credentials not configured - running in mock mode")
        
        app_state.oanda_client = OandaExecutionClient(oanda_config)
        
        # Initialize metrics collector
        metrics_port = int(os.getenv("PROMETHEUS_PORT", "8091"))
        app_state.metrics_collector = ExecutionMetricsCollector(metrics_port)
        app_state.metrics_collector.start_monitoring()
        
        # Initialize risk manager
        default_limits = RiskLimits(
            max_position_size=Decimal(os.getenv("MAX_POSITION_SIZE", "100000")),
            max_positions_per_instrument=int(os.getenv("MAX_POSITIONS_PER_INSTRUMENT", "3")),
            max_leverage=Decimal(os.getenv("MAX_LEVERAGE", "30")),
            max_daily_loss=Decimal(os.getenv("MAX_DAILY_LOSS", "1000")),
            max_drawdown=Decimal(os.getenv("MAX_DRAWDOWN", "5000")),
            required_margin_ratio=Decimal(os.getenv("REQUIRED_MARGIN_RATIO", "0.02")),
        )
        app_state.risk_manager = RiskManager(
            app_state.oanda_client,
            default_limits
        )
        
        # Initialize managers
        app_state.order_manager = OrderManager(
            app_state.oanda_client,
            app_state.risk_manager,
            app_state.metrics_collector,
            max_concurrent_orders=int(os.getenv("MAX_CONCURRENT_ORDERS", "50"))
        )
        
        app_state.position_manager = PositionManager(
            app_state.oanda_client,
            app_state.metrics_collector,
            price_update_interval=float(os.getenv("PRICE_UPDATE_INTERVAL", "1.0"))
        )
        
        # Start managers
        await app_state.order_manager.start()
        await app_state.position_manager.start()
        
        app_state.initialized = True
        logger.info("Execution Engine initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize Execution Engine", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Execution Engine")
    
    try:
        if app_state.order_manager:
            await app_state.order_manager.stop()
        
        if app_state.position_manager:
            await app_state.position_manager.stop()
        
        if app_state.oanda_client:
            await app_state.oanda_client.close()
        
        if app_state.metrics_collector:
            app_state.metrics_collector.stop_monitoring()
        
        logger.info("Execution Engine shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="TMT Execution Engine MVP",
    description="High-performance execution engine with sub-100ms order placement",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_order_manager() -> OrderManager:
    """Get order manager dependency."""
    if not app_state.initialized or not app_state.order_manager:
        raise HTTPException(status_code=503, detail="Order manager not initialized")
    return app_state.order_manager


def get_position_manager() -> PositionManager:
    """Get position manager dependency."""
    if not app_state.initialized or not app_state.position_manager:
        raise HTTPException(status_code=503, detail="Position manager not initialized")
    return app_state.position_manager


def get_risk_manager() -> RiskManager:
    """Get risk manager dependency."""
    if not app_state.initialized or not app_state.risk_manager:
        raise HTTPException(status_code=503, detail="Risk manager not initialized")
    return app_state.risk_manager


def get_metrics_collector() -> ExecutionMetricsCollector:
    """Get metrics collector dependency."""
    if not app_state.initialized or not app_state.metrics_collector:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized")
    return app_state.metrics_collector


# Health Check Endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if app_state.initialized else "initializing",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check(
    order_manager: OrderManager = Depends(get_order_manager),
    position_manager: PositionManager = Depends(get_position_manager),
    risk_manager: RiskManager = Depends(get_risk_manager),
):
    """Detailed health check with component status."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "order_manager": {
                "active_orders": len(order_manager.active_orders),
                "queue_size": order_manager.order_queue.qsize(),
                "processing_orders": len(order_manager.processing_orders),
            },
            "position_manager": {
                "accounts_monitored": len(position_manager.positions),
                "instruments_tracked": len(position_manager.current_prices),
            },
            "risk_manager": {
                "active_kill_switches": sum(1 for active in risk_manager.kill_switch_active.values() if active),
                "cached_metrics": len(risk_manager.risk_metrics_cache),
            },
        }
    }


# Order Management Endpoints

@app.post("/api/v1/orders", response_model=OrderResult, tags=["Orders"])
async def submit_order(
    order_request: OrderRequest,
    background_tasks: BackgroundTasks,
    order_manager: OrderManager = Depends(get_order_manager),
) -> OrderResult:
    """
    Submit a new order for execution.
    
    Target: < 100ms for market orders (95th percentile)
    """
    start_time = time.perf_counter()
    
    try:
        logger.info("Order submission received",
                   instrument=order_request.instrument,
                   units=order_request.units,
                   side=order_request.side,
                   order_type=order_request.type)
        
        result = await order_manager.submit_order(order_request)
        
        # Record metrics in background
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        background_tasks.add_task(
            app_state.metrics_collector.record_order_execution,
            order_request.instrument,
            order_request.type.value,
            execution_time_ms,
            result.result.value == "success",
            result.result,
            result.status
        )
        
        return result
        
    except Exception as e:
        logger.error("Order submission failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Order submission failed: {str(e)}")


@app.put("/api/v1/orders/{order_id}/modify", tags=["Orders"])
async def modify_order(
    order_id: UUID,
    modifications: Dict,
    order_manager: OrderManager = Depends(get_order_manager),
) -> Dict:
    """Modify an existing order."""
    start_time = time.perf_counter()
    
    try:
        success = await order_manager.modify_order(order_id, modifications)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Get order for instrument info
        order = await order_manager.get_order_status(order_id)
        instrument = order.instrument if order else "unknown"
        
        await app_state.metrics_collector.record_order_modification(
            instrument,
            execution_time_ms,
            success
        )
        
        if success:
            return {"status": "modified", "order_id": str(order_id)}
        else:
            raise HTTPException(status_code=400, detail="Order modification failed")
        
    except Exception as e:
        logger.error("Order modification failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Order modification failed: {str(e)}")


@app.put("/api/v1/orders/{order_id}/cancel", tags=["Orders"])
async def cancel_order(
    order_id: UUID,
    order_manager: OrderManager = Depends(get_order_manager),
) -> Dict:
    """Cancel an existing order."""
    start_time = time.perf_counter()
    
    try:
        success = await order_manager.cancel_order(order_id)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Get order for instrument info
        order = await order_manager.get_order_status(order_id)
        instrument = order.instrument if order else "unknown"
        
        await app_state.metrics_collector.record_order_cancellation(
            instrument,
            execution_time_ms,
            success
        )
        
        if success:
            return {"status": "cancelled", "order_id": str(order_id)}
        else:
            raise HTTPException(status_code=400, detail="Order cancellation failed")
        
    except Exception as e:
        logger.error("Order cancellation failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Order cancellation failed: {str(e)}")


@app.get("/api/v1/orders/{order_id}", response_model=Order, tags=["Orders"])
async def get_order_status(
    order_id: UUID,
    order_manager: OrderManager = Depends(get_order_manager),
) -> Order:
    """Get order status by ID."""
    order = await order_manager.get_order_status(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/api/v1/orders", response_model=List[Order], tags=["Orders"])
async def get_active_orders(
    account_id: Optional[str] = None,
    order_manager: OrderManager = Depends(get_order_manager),
) -> List[Order]:
    """Get active orders, optionally filtered by account."""
    return await order_manager.get_active_orders(account_id)


# Position Management Endpoints

@app.get("/api/v1/positions", response_model=List[Position], tags=["Positions"])
async def get_positions(
    account_id: str,
    position_manager: PositionManager = Depends(get_position_manager),
) -> List[Position]:
    """Get all positions for an account."""
    return await position_manager.get_positions(account_id)


@app.get("/api/v1/positions/{position_id}", response_model=Position, tags=["Positions"])
async def get_position(
    position_id: UUID,
    position_manager: PositionManager = Depends(get_position_manager),
) -> Position:
    """Get position by ID."""
    position = await position_manager.get_position(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


@app.post("/api/v1/positions/close", tags=["Positions"])
async def close_position(
    close_request: PositionCloseRequest,
    background_tasks: BackgroundTasks,
    position_manager: PositionManager = Depends(get_position_manager),
) -> Dict:
    """Close a position partially or completely."""
    start_time = time.perf_counter()
    
    try:
        success = await position_manager.close_position(close_request)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Record metrics in background
        instrument = close_request.instrument or "unknown"
        background_tasks.add_task(
            app_state.metrics_collector.record_position_close,
            instrument,
            execution_time_ms,
            success
        )
        
        if success:
            return {"status": "closed", "reason": close_request.reason}
        else:
            raise HTTPException(status_code=400, detail="Position close failed")
        
    except Exception as e:
        logger.error("Position close failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Position close failed: {str(e)}")


@app.get("/api/v1/accounts/{account_id}/summary", response_model=AccountSummary, tags=["Accounts"])
async def get_account_summary(
    account_id: str,
    position_manager: PositionManager = Depends(get_position_manager),
) -> AccountSummary:
    """Get account summary information."""
    summary = await position_manager.get_account_summary(account_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Account not found")
    return summary


# Risk Management Endpoints

@app.post("/api/v1/risk/validate", tags=["Risk Management"])
async def validate_order_risk(
    order_request: OrderRequest,
    risk_manager: RiskManager = Depends(get_risk_manager),
) -> Dict:
    """Validate order against risk limits."""
    start_time = time.perf_counter()
    
    try:
        order = order_request.to_order()
        validation_result = await risk_manager.validate_order(order)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Record metrics
        risk_manager.record_risk_validation(
            execution_time_ms,
            None if validation_result.is_valid else validation_result.error_code,
            order.account_id
        )
        
        return {
            "valid": validation_result.is_valid,
            "error_code": validation_result.error_code,
            "error_message": validation_result.error_message,
            "warnings": validation_result.warnings,
        }
        
    except Exception as e:
        logger.error("Risk validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Risk validation failed: {str(e)}")


@app.get("/api/v1/risk/{account_id}/metrics", tags=["Risk Management"])
async def get_risk_metrics(
    account_id: str,
    risk_manager: RiskManager = Depends(get_risk_manager),
) -> Dict:
    """Get current risk metrics for an account."""
    try:
        risk_metrics = await risk_manager.check_risk_limits(account_id)
        return {
            "account_id": account_id,
            "current_leverage": float(risk_metrics.current_leverage),
            "margin_utilization": float(risk_metrics.margin_utilization),
            "position_count": risk_metrics.position_count,
            "daily_pl": float(risk_metrics.daily_pl),
            "max_position_size": float(risk_metrics.max_position_size),
            "risk_score": risk_metrics.risk_score,
        }
        
    except Exception as e:
        logger.error("Risk metrics failed", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Risk metrics failed: {str(e)}")


@app.post("/api/v1/risk/{account_id}/kill-switch", tags=["Risk Management"])
async def activate_kill_switch(
    account_id: str,
    reason: str,
    risk_manager: RiskManager = Depends(get_risk_manager),
    metrics_collector: ExecutionMetricsCollector = Depends(get_metrics_collector),
) -> Dict:
    """Activate kill switch for an account."""
    try:
        risk_manager.activate_kill_switch(account_id, reason)
        metrics_collector.record_kill_switch_activation(account_id, reason)
        
        return {
            "status": "activated",
            "account_id": account_id,
            "reason": reason,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Kill switch activation failed", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Kill switch activation failed: {str(e)}")


@app.delete("/api/v1/risk/{account_id}/kill-switch", tags=["Risk Management"])
async def deactivate_kill_switch(
    account_id: str,
    reason: str,
    risk_manager: RiskManager = Depends(get_risk_manager),
) -> Dict:
    """Deactivate kill switch for an account."""
    try:
        risk_manager.deactivate_kill_switch(account_id, reason)
        
        return {
            "status": "deactivated",
            "account_id": account_id,
            "reason": reason,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Kill switch deactivation failed", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Kill switch deactivation failed: {str(e)}")


# Emergency Stop Endpoints

@app.post("/api/v1/emergency-stop", tags=["Emergency"])
async def emergency_stop(
    background_tasks: BackgroundTasks,
    reason: str = "Emergency stop triggered",
    position_manager: PositionManager = Depends(get_position_manager),
    risk_manager: RiskManager = Depends(get_risk_manager),
    metrics_collector: ExecutionMetricsCollector = Depends(get_metrics_collector),
) -> Dict:
    """
    Emergency stop - immediately close all positions across all accounts.
    
    This is a critical safety endpoint that:
    1. Activates kill switches for all accounts
    2. Closes all open positions immediately
    3. Records emergency stop metrics
    
    Use only in emergency situations.
    """
    start_time = time.perf_counter()
    
    try:
        logger.critical("🚨 EMERGENCY STOP ACTIVATED", reason=reason)
        
        # Get all accounts with open positions
        all_positions = []
        for account_id, instruments in position_manager.positions.items():
            for instrument, position in instruments.items():
                if position.is_open():
                    all_positions.append({
                        "account_id": account_id,
                        "instrument": instrument, 
                        "position": position
                    })
        
        logger.warning(f"Emergency stop: Found {len(all_positions)} open positions to close")
        
        # Activate kill switches for all accounts
        affected_accounts = set()
        for pos_info in all_positions:
            account_id = pos_info["account_id"]
            affected_accounts.add(account_id)
            risk_manager.activate_kill_switch(account_id, f"Emergency stop: {reason}")
        
        # Close all positions in parallel for speed
        close_tasks = []
        for pos_info in all_positions:
            close_request = PositionCloseRequest(
                account_id=pos_info["account_id"],
                instrument=pos_info["instrument"],
                units=None,  # Close entire position
                reason=f"Emergency stop: {reason}"
            )
            
            task = asyncio.create_task(
                position_manager.close_position(close_request)
            )
            close_tasks.append({
                "task": task,
                "account_id": pos_info["account_id"], 
                "instrument": pos_info["instrument"]
            })
        
        # Wait for all position closures with timeout
        if close_tasks:
            logger.warning(f"Executing emergency closure of {len(close_tasks)} positions...")
            
            results = []
            for task_info in close_tasks:
                try:
                    # Give each position 30 seconds to close
                    success = await asyncio.wait_for(task_info["task"], timeout=30.0)
                    results.append({
                        "account_id": task_info["account_id"],
                        "instrument": task_info["instrument"],
                        "success": success
                    })
                    
                    if success:
                        logger.info(f"✓ Position closed: {task_info['account_id']}/{task_info['instrument']}")
                    else:
                        logger.error(f"✗ Failed to close: {task_info['account_id']}/{task_info['instrument']}")
                        
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Timeout closing: {task_info['account_id']}/{task_info['instrument']}")
                    results.append({
                        "account_id": task_info["account_id"],
                        "instrument": task_info["instrument"], 
                        "success": False,
                        "error": "timeout"
                    })
                except Exception as e:
                    logger.error(f"💥 Exception closing: {task_info['account_id']}/{task_info['instrument']}: {e}")
                    results.append({
                        "account_id": task_info["account_id"],
                        "instrument": task_info["instrument"],
                        "success": False, 
                        "error": str(e)
                    })
            
            successful_closes = sum(1 for r in results if r["success"])
            failed_closes = len(results) - successful_closes
            
        else:
            results = []
            successful_closes = 0
            failed_closes = 0
            logger.info("No open positions found during emergency stop")
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Record emergency stop metrics
        background_tasks.add_task(
            metrics_collector.record_emergency_stop,
            reason,
            len(all_positions),
            successful_closes,
            failed_closes,
            execution_time_ms
        )
        
        logger.critical(
            "🚨 EMERGENCY STOP COMPLETED",
            execution_time_ms=execution_time_ms,
            positions_found=len(all_positions),
            successful_closes=successful_closes,
            failed_closes=failed_closes,
            affected_accounts=len(affected_accounts)
        )
        
        return {
            "status": "emergency_stop_executed",
            "reason": reason,
            "execution_time_ms": execution_time_ms,
            "summary": {
                "positions_found": len(all_positions),
                "successful_closes": successful_closes,
                "failed_closes": failed_closes,
                "affected_accounts": list(affected_accounts)
            },
            "results": results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Emergency stop failed", error=str(e), execution_time_ms=execution_time_ms)
        
        # Still try to record the failure
        background_tasks.add_task(
            metrics_collector.record_emergency_stop_failure,
            reason,
            str(e),
            execution_time_ms
        )
        
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")


@app.post("/api/v1/emergency-stop/{account_id}", tags=["Emergency"]) 
async def emergency_stop_account(
    account_id: str,
    background_tasks: BackgroundTasks,
    reason: str = "Emergency stop triggered for account",
    position_manager: PositionManager = Depends(get_position_manager),
    risk_manager: RiskManager = Depends(get_risk_manager),
    metrics_collector: ExecutionMetricsCollector = Depends(get_metrics_collector),
) -> Dict:
    """
    Emergency stop for a specific account - close all positions for the account.
    """
    start_time = time.perf_counter()
    
    try:
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED FOR ACCOUNT {account_id}", reason=reason)
        
        # Get all open positions for this account
        account_positions = []
        if account_id in position_manager.positions:
            for instrument, position in position_manager.positions[account_id].items():
                if position.is_open():
                    account_positions.append({
                        "instrument": instrument,
                        "position": position
                    })
        
        logger.warning(f"Emergency stop: Found {len(account_positions)} open positions for account {account_id}")
        
        # Activate kill switch for the account
        risk_manager.activate_kill_switch(account_id, f"Emergency stop: {reason}")
        
        # Close all positions for this account
        close_tasks = []
        for pos_info in account_positions:
            close_request = PositionCloseRequest(
                account_id=account_id,
                instrument=pos_info["instrument"],
                units=None,  # Close entire position
                reason=f"Emergency stop: {reason}"
            )
            
            task = asyncio.create_task(
                position_manager.close_position(close_request)
            )
            close_tasks.append({
                "task": task,
                "instrument": pos_info["instrument"]
            })
        
        # Wait for all position closures
        if close_tasks:
            logger.warning(f"Executing emergency closure of {len(close_tasks)} positions for account {account_id}")
            
            results = []
            for task_info in close_tasks:
                try:
                    success = await asyncio.wait_for(task_info["task"], timeout=30.0)
                    results.append({
                        "instrument": task_info["instrument"],
                        "success": success
                    })
                    
                    if success:
                        logger.info(f"✓ Position closed: {account_id}/{task_info['instrument']}")
                    else:
                        logger.error(f"✗ Failed to close: {account_id}/{task_info['instrument']}")
                        
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Timeout closing: {account_id}/{task_info['instrument']}")
                    results.append({
                        "instrument": task_info["instrument"],
                        "success": False,
                        "error": "timeout"
                    })
                except Exception as e:
                    logger.error(f"💥 Exception closing: {account_id}/{task_info['instrument']}: {e}")
                    results.append({
                        "instrument": task_info["instrument"],
                        "success": False,
                        "error": str(e)
                    })
            
            successful_closes = sum(1 for r in results if r["success"])
            failed_closes = len(results) - successful_closes
        else:
            results = []
            successful_closes = 0
            failed_closes = 0
            logger.info(f"No open positions found for account {account_id} during emergency stop")
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Record metrics
        background_tasks.add_task(
            metrics_collector.record_account_emergency_stop,
            account_id,
            reason,
            len(account_positions),
            successful_closes,
            failed_closes,
            execution_time_ms
        )
        
        logger.critical(
            f"🚨 EMERGENCY STOP COMPLETED FOR ACCOUNT {account_id}",
            execution_time_ms=execution_time_ms,
            positions_found=len(account_positions),
            successful_closes=successful_closes,
            failed_closes=failed_closes
        )
        
        return {
            "status": "emergency_stop_executed",
            "account_id": account_id,
            "reason": reason,
            "execution_time_ms": execution_time_ms,
            "summary": {
                "positions_found": len(account_positions),
                "successful_closes": successful_closes,
                "failed_closes": failed_closes
            },
            "results": results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Emergency stop failed for account {account_id}", error=str(e))
        
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")


# Performance and Monitoring Endpoints

@app.get("/api/v1/performance/metrics", tags=["Performance"])
async def get_performance_metrics(
    order_manager: OrderManager = Depends(get_order_manager),
    position_manager: PositionManager = Depends(get_position_manager),
    metrics_collector: ExecutionMetricsCollector = Depends(get_metrics_collector),
) -> Dict:
    """Get comprehensive performance metrics."""
    return {
        "execution_engine": {
            "order_manager": order_manager.get_performance_metrics(),
            "position_manager": position_manager.get_performance_metrics(),
            "metrics_summary": metrics_collector.get_performance_summary(),
        },
        "oanda_client": app_state.oanda_client.get_performance_metrics() if app_state.oanda_client else {},
        "timestamp": time.time(),
    }


@app.get("/api/v1/performance/fill-rates", tags=["Performance"])
async def get_fill_rates(
    metrics_collector: ExecutionMetricsCollector = Depends(get_metrics_collector),
) -> Dict:
    """Get order fill rates by instrument and order type."""
    return {
        "fill_rates": metrics_collector.get_fill_rates(),
        "timestamp": time.time(),
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", 
                path=str(request.url),
                method=request.method,
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8004"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logger.info("Starting Execution Engine MVP",
               host=host,
               port=port,
               log_level=log_level)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        access_log=False,
    )