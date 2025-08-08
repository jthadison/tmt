"""Main FastAPI application for the Performance Tracker Agent."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    Base, PerformanceMetricsData, PnLSnapshot, AccountComparison,
    ExportRequest, PerformanceReport, PeriodType
)
from .pnl_tracker import PnLCalculationEngine, PnLTracker
from .metrics_calculator import PerformanceMetricsCalculator
from .report_generator import PerformanceReportGenerator
from .account_comparison import AccountComparisonSystem
from .export_manager import PerformanceExportManager
from .data_retention import DataRetentionManager
from .market_data import MarketDataFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql://user:password@localhost:5432/trading_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global services
pnl_tracker: Optional[PnLTracker] = None
market_data_feed: Optional[MarketDataFeed] = None
data_retention_manager: Optional[DataRetentionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global pnl_tracker, market_data_feed, data_retention_manager
    
    logger.info("Starting Performance Tracker Agent...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize services
    db = SessionLocal()
    try:
        # Initialize market data feed
        market_data_feed = MarketDataFeed()
        await market_data_feed.start_feed()
        
        # Initialize P&L tracker
        pnl_tracker = PnLTracker(db, market_data_feed)
        await pnl_tracker.start_tracking()
        
        # Initialize data retention manager
        data_retention_manager = DataRetentionManager(db)
        await data_retention_manager.start_retention_manager()
        
        logger.info("Performance Tracker Agent started successfully")
        
        yield
        
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Performance Tracker Agent...")
        
        if pnl_tracker:
            await pnl_tracker.stop_tracking()
        
        if market_data_feed:
            await market_data_feed.stop_feed()
        
        db.close()
        logger.info("Performance Tracker Agent shutdown complete")


app = FastAPI(
    title="Performance Tracker Agent",
    description="Real-time performance tracking and analytics for trading accounts",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API requests/responses
class PnLRequest(BaseModel):
    account_id: UUID
    include_unrealized: bool = True


class MetricsRequest(BaseModel):
    account_id: UUID
    start_date: datetime
    end_date: datetime
    period_type: PeriodType = PeriodType.DAILY


class ReportRequest(BaseModel):
    account_id: UUID
    report_type: str = Field(..., description="daily, weekly, monthly, ytd, custom")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ComparisonRequest(BaseModel):
    account_ids: List[UUID]
    start_date: datetime
    end_date: datetime
    period_type: PeriodType = PeriodType.MONTHLY


class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if self.active_connections:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn)


websocket_manager = WebSocketManager()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "pnl_tracker": pnl_tracker is not None and pnl_tracker.is_running,
            "market_data": market_data_feed is not None and market_data_feed.is_running,
            "data_retention": data_retention_manager is not None
        }
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time performance updates."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# P&L Tracking endpoints
@app.get("/api/v1/performance/pnl/{account_id}", response_model=PnLSnapshot)
async def get_real_time_pnl(
    account_id: UUID,
    include_unrealized: bool = True,
    db: Session = Depends(get_db)
):
    """Get real-time P&L for an account."""
    try:
        if not pnl_tracker:
            raise HTTPException(status_code=503, detail="P&L tracker not available")
        
        pnl_data = await pnl_tracker.get_current_pnl(account_id, include_unrealized)
        
        if not pnl_data:
            raise HTTPException(status_code=404, detail="Account P&L not found")
        
        return pnl_data
        
    except Exception as e:
        logger.error(f"Error getting real-time P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/performance/metrics/{account_id}", response_model=PerformanceMetricsData)
async def get_performance_metrics(
    account_id: UUID,
    start_date: datetime,
    end_date: datetime,
    period_type: PeriodType = PeriodType.DAILY,
    db: Session = Depends(get_db)
):
    """Get performance metrics for an account."""
    try:
        calculator = PerformanceMetricsCalculator(db)
        metrics = await calculator.calculate_period_metrics(
            account_id, start_date, end_date, period_type
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Report generation endpoints
@app.post("/api/v1/performance/report")
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate performance report."""
    try:
        report_generator = PerformanceReportGenerator(db)
        
        if request.report_type == "daily":
            report_date = request.start_date or datetime.utcnow()
            report = await report_generator.generate_daily_report(
                request.account_id, report_date
            )
            return report.dict()
            
        elif request.report_type == "weekly":
            week_start = request.start_date or datetime.utcnow() - timedelta(days=7)
            report = await report_generator.generate_weekly_report(
                request.account_id, week_start
            )
            return report
            
        elif request.report_type == "monthly":
            month_start = request.start_date or datetime.utcnow().replace(day=1)
            report = await report_generator.generate_monthly_report(
                request.account_id, month_start
            )
            return report
            
        elif request.report_type == "ytd":
            current_date = request.end_date or datetime.utcnow()
            report = await report_generator.generate_ytd_report(
                request.account_id, current_date
            )
            return report
            
        elif request.report_type == "custom":
            if not request.start_date or not request.end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="start_date and end_date required for custom reports"
                )
            
            report = await report_generator.generate_custom_period_report(
                request.account_id, request.start_date, request.end_date
            )
            return report
            
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid report_type. Must be: daily, weekly, monthly, ytd, custom"
            )
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Account comparison endpoints
@app.post("/api/v1/performance/compare")
async def compare_accounts(
    request: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """Compare performance across multiple accounts."""
    try:
        comparison_system = AccountComparisonSystem(db)
        
        rankings = await comparison_system.calculate_account_rankings(
            request.account_ids,
            request.start_date,
            request.end_date,
            request.period_type
        )
        
        return {
            "comparison_period": {
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "period_type": request.period_type.value
            },
            "rankings": [ranking.dict() for ranking in rankings]
        }
        
    except Exception as e:
        logger.error(f"Error comparing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/performance/compare/best-worst")
async def get_best_worst_performers(
    account_ids: List[UUID],
    start_date: datetime,
    end_date: datetime,
    period_type: PeriodType = PeriodType.MONTHLY,
    db: Session = Depends(get_db)
):
    """Get best and worst performing accounts."""
    try:
        comparison_system = AccountComparisonSystem(db)
        
        performers = await comparison_system.get_best_worst_performers(
            account_ids, start_date, end_date, period_type
        )
        
        return performers
        
    except Exception as e:
        logger.error(f"Error getting best/worst performers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/performance/heatmap")
async def generate_performance_heatmap(
    account_ids: List[UUID],
    start_date: datetime,
    end_date: datetime,
    metric_type: str = "total_pnl",
    db: Session = Depends(get_db)
):
    """Generate performance heatmap data."""
    try:
        comparison_system = AccountComparisonSystem(db)
        
        heatmap_data = await comparison_system.generate_performance_heatmap_data(
            account_ids, start_date, end_date, metric_type
        )
        
        return heatmap_data
        
    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export endpoints
@app.post("/api/v1/performance/export")
async def export_performance_data(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Export performance data in various formats."""
    try:
        export_manager = PerformanceExportManager(db)
        
        export_result = await export_manager.export_performance_data(request)
        
        return {
            "export_id": str(uuid4()),
            "filename": export_result["filename"],
            "content_type": export_result["content_type"],
            "size": len(export_result["content"]),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data retention endpoints
@app.post("/api/v1/performance/retention/apply")
async def apply_retention_policy(
    table_name: str,
    db: Session = Depends(get_db)
):
    """Apply data retention policy to specific table."""
    try:
        if not data_retention_manager:
            raise HTTPException(status_code=503, detail="Data retention manager not available")
        
        results = await data_retention_manager.apply_retention_policy(table_name)
        
        return {
            "table_name": table_name,
            "retention_results": results,
            "applied_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error applying retention policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/performance/retention/backup")
async def create_data_backup(
    backup_type: str = "incremental",
    db: Session = Depends(get_db)
):
    """Create performance data backup."""
    try:
        if not data_retention_manager:
            raise HTTPException(status_code=503, detail="Data retention manager not available")
        
        backup_info = await data_retention_manager.create_data_backup(backup_type)
        
        return backup_info
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/performance/retention/integrity")
async def verify_data_integrity(db: Session = Depends(get_db)):
    """Verify data integrity and consistency."""
    try:
        if not data_retention_manager:
            raise HTTPException(status_code=503, detail="Data retention manager not available")
        
        integrity_report = await data_retention_manager.verify_data_integrity()
        
        return integrity_report
        
    except Exception as e:
        logger.error(f"Error verifying data integrity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Historical data endpoints
@app.get("/api/v1/performance/history/{account_id}")
async def get_account_history(
    account_id: UUID,
    start_date: datetime,
    end_date: datetime,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Get historical performance data for an account."""
    try:
        # This would integrate with the existing models to retrieve historical data
        return {
            "account_id": str(account_id),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "data": [],  # Placeholder for historical data
            "total_records": 0,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting account history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task for broadcasting P&L updates
async def broadcast_pnl_updates():
    """Background task to broadcast P&L updates via WebSocket."""
    while True:
        try:
            if pnl_tracker and websocket_manager.active_connections:
                # Get latest P&L snapshots
                latest_updates = await pnl_tracker.get_all_accounts_pnl()
                
                if latest_updates:
                    await websocket_manager.broadcast({
                        "type": "pnl_update",
                        "data": latest_updates,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            await asyncio.sleep(1)  # Broadcast every second
            
        except Exception as e:
            logger.error(f"Error in P&L broadcast task: {e}")
            await asyncio.sleep(5)  # Wait longer on error


# Start background tasks on startup
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks."""
    asyncio.create_task(broadcast_pnl_updates())


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )