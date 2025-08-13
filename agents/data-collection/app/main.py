"""
Data Collection Agent FastAPI Application.

This is the main entry point for the Performance Data Collection Pipeline agent,
providing REST API endpoints for data ingestion, validation, and analysis.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .pipeline import DataCollectionPipeline, PipelineConfig
from .data_models import TradeEvent, ComprehensiveTradeRecord
from .storage_manager import DataStorageManager
from .pattern_tracker import PatternPerformanceAnalyzer
from .execution_analyzer import ExecutionQualityReporter
from .false_signal_analyzer import RejectedSignalAnalyzer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global instances
pipeline: Optional[DataCollectionPipeline] = None
storage_manager: Optional[DataStorageManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global pipeline, storage_manager
    
    # Startup
    logger.info("Starting Data Collection Agent...")
    
    # Initialize components
    pipeline_config = PipelineConfig(
        validate_data=True,
        store_invalid_data=True,
        enable_pattern_tracking=True,
        enable_execution_analysis=True,
        enable_false_signal_analysis=True
    )
    
    pipeline = DataCollectionPipeline(pipeline_config)
    storage_manager = DataStorageManager()
    
    logger.info("Data Collection Agent started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Collection Agent...")


# Create FastAPI app
app = FastAPI(
    title="Data Collection Agent",
    description="Performance Data Collection Pipeline for Trading System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests/responses
class TradeEventRequest(BaseModel):
    """Request model for trade event ingestion."""
    trade_id: str
    account_id: str
    event_type: str
    timestamp: datetime
    event_data: Dict[str, Any]
    market_data: Dict[str, Any] = Field(default_factory=dict)
    signal_data: Dict[str, Any] = Field(default_factory=dict)
    execution_data: Dict[str, Any] = Field(default_factory=dict)


class TradeQueryRequest(BaseModel):
    """Request model for trade queries."""
    start_time: datetime
    end_time: datetime
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = Field(default=1000, le=10000)


class PatternAnalysisRequest(BaseModel):
    """Request model for pattern analysis."""
    pattern_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    minimum_trades: int = Field(default=10, ge=1)


class ExecutionQualityRequest(BaseModel):
    """Request model for execution quality analysis."""
    start_time: datetime
    end_time: datetime
    symbols: Optional[List[str]] = None
    accounts: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    pipeline_metrics: Dict[str, Any]
    storage_stats: Dict[str, Any]


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    
    if not pipeline or not storage_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        pipeline_metrics=pipeline.get_pipeline_metrics(),
        storage_stats=storage_manager.get_storage_statistics()
    )


# Data ingestion endpoints
@app.post("/api/v1/ingest/trade-event")
async def ingest_trade_event(
    request: TradeEventRequest,
    background_tasks: BackgroundTasks
):
    """Ingest a trade event into the data collection pipeline."""
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not available")
    
    try:
        # Create trade event
        trade_event = TradeEvent(
            trade_id=request.trade_id,
            account_id=request.account_id,
            event_type=request.event_type,
            timestamp=request.timestamp,
            event_data=request.event_data,
            market_data=request.market_data,
            signal_data=request.signal_data,
            execution_data=request.execution_data
        )
        
        # Process event asynchronously
        record = await pipeline.process_trade_event(trade_event)
        
        if record:
            # Store record in background
            background_tasks.add_task(store_record_background, record)
            
            return {
                "status": "success",
                "message": "Trade event processed successfully",
                "record_id": record.id,
                "learning_eligible": record.learning_metadata.learning_eligible,
                "data_quality": float(record.learning_metadata.data_quality)
            }
        else:
            return {
                "status": "error",
                "message": "Failed to process trade event",
                "record_id": None
            }
            
    except Exception as e:
        logger.error(f"Error ingesting trade event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest/batch")
async def ingest_batch_events(
    events: List[TradeEventRequest],
    background_tasks: BackgroundTasks
):
    """Ingest multiple trade events in batch."""
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not available")
    
    if len(events) > 100:
        raise HTTPException(status_code=400, detail="Batch size too large (max 100)")
    
    results = []
    
    try:
        for event_request in events:
            trade_event = TradeEvent(
                trade_id=event_request.trade_id,
                account_id=event_request.account_id,
                event_type=event_request.event_type,
                timestamp=event_request.timestamp,
                event_data=event_request.event_data,
                market_data=event_request.market_data,
                signal_data=event_request.signal_data,
                execution_data=event_request.execution_data
            )
            
            record = await pipeline.process_trade_event(trade_event)
            
            if record:
                background_tasks.add_task(store_record_background, record)
                results.append({
                    "trade_id": event_request.trade_id,
                    "status": "success",
                    "record_id": record.id
                })
            else:
                results.append({
                    "trade_id": event_request.trade_id,
                    "status": "failed",
                    "record_id": None
                })
        
        successful_count = len([r for r in results if r["status"] == "success"])
        
        return {
            "status": "completed",
            "total_events": len(events),
            "successful": successful_count,
            "failed": len(events) - successful_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Query endpoints
@app.post("/api/v1/query/trades")
async def query_trades(request: TradeQueryRequest):
    """Query trade records with filters."""
    
    if not storage_manager:
        raise HTTPException(status_code=503, detail="Storage manager not available")
    
    try:
        records = storage_manager.query_trades(
            start_time=request.start_time,
            end_time=request.end_time,
            filters=request.filters,
            limit=request.limit
        )
        
        return {
            "status": "success",
            "count": len(records),
            "records": [record.__dict__ for record in records]  # Simplified serialization
        }
        
    except Exception as e:
        logger.error(f"Error querying trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Analysis endpoints
@app.post("/api/v1/analysis/patterns")
async def analyze_patterns(request: PatternAnalysisRequest):
    """Analyze pattern performance."""
    
    if not pipeline or not pipeline.pattern_analyzer:
        raise HTTPException(status_code=503, detail="Pattern analyzer not available")
    
    try:
        # In real implementation, would query actual trade data
        trades = []  # Would fetch from storage_manager
        
        if request.pattern_id:
            # Analyze specific pattern
            pattern_performance = pipeline.pattern_analyzer.analyze_pattern_performance(
                request.pattern_id, trades
            )
            
            return {
                "status": "success",
                "pattern_performance": pattern_performance.__dict__
            }
        else:
            # Analyze all patterns
            # In real implementation, would group trades by pattern and analyze each
            return {
                "status": "success",
                "message": "Pattern analysis not implemented for all patterns query"
            }
            
    except Exception as e:
        logger.error(f"Error analyzing patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analysis/execution-quality")
async def analyze_execution_quality(request: ExecutionQualityRequest):
    """Analyze execution quality metrics."""
    
    if not pipeline or not pipeline.execution_analyzer:
        raise HTTPException(status_code=503, detail="Execution analyzer not available")
    
    try:
        # In real implementation, would query trades with filters
        trades = []  # Would fetch from storage_manager based on request filters
        
        quality_metrics = pipeline.execution_analyzer.generate_execution_quality_report(
            trades, request.start_time, request.end_time
        )
        
        return {
            "status": "success",
            "execution_quality": quality_metrics.__dict__
        }
        
    except Exception as e:
        logger.error(f"Error analyzing execution quality: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analysis/false-signals")
async def analyze_false_signals(
    start_time: datetime,
    end_time: datetime,
    min_sample_size: int = 10
):
    """Analyze false signal patterns."""
    
    if not pipeline or not pipeline.false_signal_analyzer:
        raise HTTPException(status_code=503, detail="False signal analyzer not available")
    
    try:
        # In real implementation, would fetch rejection analyses from storage
        rejection_analyses = []  # Would fetch from storage_manager
        
        false_positive_patterns = pipeline.false_signal_analyzer.rejection_analyzer.detect_false_positive_patterns(
            rejection_analyses, min_sample_size
        )
        
        return {
            "status": "success",
            "false_positive_patterns": false_positive_patterns
        }
        
    except Exception as e:
        logger.error(f"Error analyzing false signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Validation and quality endpoints
@app.get("/api/v1/validation/report")
async def get_validation_report(
    start_time: datetime,
    end_time: datetime
):
    """Get data validation report."""
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not available")
    
    try:
        report = await pipeline.generate_quality_report(start_time, end_time)
        
        return {
            "status": "success",
            "validation_report": report
        }
        
    except Exception as e:
        logger.error(f"Error generating validation report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics and monitoring endpoints
@app.get("/api/v1/metrics/pipeline")
async def get_pipeline_metrics():
    """Get pipeline performance metrics."""
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not available")
    
    return {
        "status": "success",
        "metrics": pipeline.get_pipeline_metrics()
    }


@app.get("/api/v1/metrics/storage")
async def get_storage_metrics():
    """Get storage performance metrics."""
    
    if not storage_manager:
        raise HTTPException(status_code=503, detail="Storage manager not available")
    
    return {
        "status": "success",
        "storage_stats": storage_manager.get_storage_statistics()
    }


# Optimization endpoints
@app.post("/api/v1/optimize/storage")
async def optimize_storage(background_tasks: BackgroundTasks):
    """Trigger storage optimization process."""
    
    if not storage_manager:
        raise HTTPException(status_code=503, detail="Storage manager not available")
    
    # Run optimization in background
    background_tasks.add_task(run_storage_optimization)
    
    return {
        "status": "success",
        "message": "Storage optimization started in background"
    }


# Background tasks
async def store_record_background(record: ComprehensiveTradeRecord):
    """Background task to store record."""
    
    if storage_manager:
        success = storage_manager.store_trade_record(record)
        if success:
            logger.debug(f"Background storage successful for record {record.id}")
        else:
            logger.error(f"Background storage failed for record {record.id}")


async def run_storage_optimization():
    """Background task for storage optimization."""
    
    if storage_manager:
        try:
            results = storage_manager.optimize_storage()
            logger.info(f"Storage optimization completed: {results}")
        except Exception as e:
            logger.error(f"Storage optimization failed: {str(e)}")


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )