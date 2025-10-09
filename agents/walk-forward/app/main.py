"""
Walk-Forward Optimization Service - Story 11.3, Task 8

FastAPI REST API for walk-forward optimization:
- POST /api/walk-forward/run - Start optimization job
- GET /api/walk-forward/status/{job_id} - Check job status
- GET /api/walk-forward/results/{job_id} - Get results
- GET /api/walk-forward/report/{job_id} - Get formatted report
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import uuid
import logging
from pathlib import Path

from .models import (
    WalkForwardConfig, WalkForwardResult, OptimizationJob,
    WindowType, OptimizationMethod
)
from .optimizer import WalkForwardOptimizer
from .report_generator import WalkForwardReportGenerator
from .visualization import VisualizationDataGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Walk-Forward Optimization Service",
    description="Validates trading parameters using walk-forward optimization",
    version="1.0.0"
)

# In-memory job storage (in production, use database)
jobs: Dict[str, OptimizationJob] = {}
results: Dict[str, WalkForwardResult] = {}

# Report storage directory
REPORT_DIR = Path("./reports")
REPORT_DIR.mkdir(exist_ok=True)


# API Models
class RunWalkForwardRequest(BaseModel):
    """Request model for running walk-forward optimization"""
    start_date: datetime
    end_date: datetime
    training_window_days: int = 90
    testing_window_days: int = 30
    step_size_days: int = 30
    window_type: str = "rolling"
    instruments: List[str]
    initial_capital: float = 100000.0
    risk_percentage: float = 0.02
    parameter_ranges: Dict[str, tuple]
    baseline_parameters: Dict[str, Any]
    optimization_method: str = "bayesian"
    max_iterations: Optional[int] = 100
    n_workers: int = 4


class WalkForwardStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    progress: float
    current_window: int
    total_windows: int
    created_at: datetime
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]


class APIResponse(BaseModel):
    """Standardized API response wrapper"""
    data: Optional[Any] = None
    error: Optional[str] = None
    correlation_id: str


# Helper functions
def create_correlation_id() -> str:
    """Generate unique correlation ID"""
    return str(uuid.uuid4())


async def run_optimization_job(job_id: str, config: WalkForwardConfig):
    """
    Background task to run walk-forward optimization

    Args:
        job_id: Job identifier
        config: Walk-forward configuration
    """
    try:
        # Update job status
        jobs[job_id].status = "running"
        jobs[job_id].started_at = datetime.utcnow()

        logger.info(f"Starting walk-forward optimization job {job_id}")

        # Get data repository (mocked for now - in production, inject properly)
        from app.repositories.historical_data_repository import HistoricalDataRepository
        from app.database import get_db

        # Create optimizer
        async for db in get_db():
            data_repo = HistoricalDataRepository(db)

            optimizer = WalkForwardOptimizer(config, data_repo)

            # Run optimization
            result = await optimizer.run(job_id)

            # Store result
            results[job_id] = result

            # Update job
            jobs[job_id].status = "completed"
            jobs[job_id].completed_at = datetime.utcnow()
            jobs[job_id].progress = 100.0
            jobs[job_id].result = result

            logger.info(
                f"Walk-forward optimization job {job_id} completed: "
                f"{result.acceptance_status}"
            )

            # Generate reports
            report_gen = WalkForwardReportGenerator()
            report_files = report_gen.generate_all_reports(
                result,
                str(REPORT_DIR / job_id)
            )

            logger.info(f"Reports generated for job {job_id}: {report_files}")

            break

    except Exception as e:
        logger.error(f"Error in job {job_id}: {str(e)}", exc_info=True)

        # Update job with error
        jobs[job_id].status = "failed"
        jobs[job_id].completed_at = datetime.utcnow()
        jobs[job_id].error_message = str(e)


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "walk-forward-optimization"}


@app.post("/api/walk-forward/run")
async def run_walk_forward(
    request: RunWalkForwardRequest,
    background_tasks: BackgroundTasks
) -> APIResponse:
    """
    Start walk-forward optimization job

    Runs asynchronously in background and returns job ID for status polling.

    Args:
        request: Walk-forward configuration
        background_tasks: FastAPI background tasks

    Returns:
        APIResponse with job ID and estimated completion
    """
    correlation_id = create_correlation_id()

    try:
        # Create config
        config = WalkForwardConfig(
            start_date=request.start_date,
            end_date=request.end_date,
            training_window_days=request.training_window_days,
            testing_window_days=request.testing_window_days,
            step_size_days=request.step_size_days,
            window_type=WindowType(request.window_type),
            instruments=request.instruments,
            initial_capital=request.initial_capital,
            risk_percentage=request.risk_percentage,
            parameter_ranges=request.parameter_ranges,
            baseline_parameters=request.baseline_parameters,
            optimization_method=OptimizationMethod(request.optimization_method),
            max_iterations=request.max_iterations,
            n_workers=request.n_workers
        )

        # Generate job ID
        job_id = f"wf-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"

        # Calculate total windows
        optimizer = WalkForwardOptimizer(config, None)  # Temporary for window calculation
        windows = optimizer.generate_windows()
        total_windows = len(windows)

        # Create job
        job = OptimizationJob(
            job_id=job_id,
            status="pending",
            config=config,
            total_windows=total_windows,
            created_at=datetime.utcnow()
        )

        jobs[job_id] = job

        # Start background task
        background_tasks.add_task(run_optimization_job, job_id, config)

        logger.info(f"Created walk-forward job {job_id} with {total_windows} windows")

        return APIResponse(
            data={
                "job_id": job_id,
                "status": "pending",
                "total_windows": total_windows,
                "estimated_completion": None  # Could calculate based on historical performance
            },
            error=None,
            correlation_id=correlation_id
        )

    except Exception as e:
        logger.error(f"Error creating walk-forward job: {str(e)}", exc_info=True)
        return APIResponse(
            data=None,
            error=str(e),
            correlation_id=correlation_id
        )


@app.get("/api/walk-forward/status/{job_id}")
async def get_job_status(job_id: str) -> APIResponse:
    """
    Get walk-forward optimization job status

    Args:
        job_id: Job identifier

    Returns:
        APIResponse with job status
    """
    correlation_id = create_correlation_id()

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]

    return APIResponse(
        data=WalkForwardStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_window=job.current_window,
            total_windows=job.total_windows,
            created_at=job.created_at,
            started_at=job.started_at,
            estimated_completion=job.estimated_completion
        ),
        error=None,
        correlation_id=correlation_id
    )


@app.get("/api/walk-forward/results/{job_id}")
async def get_job_results(job_id: str) -> APIResponse:
    """
    Get walk-forward optimization results

    Args:
        job_id: Job identifier

    Returns:
        APIResponse with complete walk-forward results
    """
    correlation_id = create_correlation_id()

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed yet (status: {job.status})"
        )

    if job_id not in results:
        raise HTTPException(status_code=404, detail=f"Results for job {job_id} not found")

    result = results[job_id]

    return APIResponse(
        data=result.model_dump(mode='json'),
        error=None,
        correlation_id=correlation_id
    )


@app.get("/api/walk-forward/report/{job_id}")
async def get_job_report(
    job_id: str,
    format: str = Query("json", regex="^(json|text)$")
) -> Any:
    """
    Get formatted report for walk-forward optimization

    Args:
        job_id: Job identifier
        format: Report format ('json' or 'text')

    Returns:
        Formatted report
    """
    if job_id not in results:
        raise HTTPException(status_code=404, detail=f"Results for job {job_id} not found")

    result = results[job_id]
    report_gen = WalkForwardReportGenerator()

    if format == "json":
        report_path = REPORT_DIR / job_id / f"walk_forward_report_{job_id}.json"
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="JSON report not found")
        return FileResponse(report_path, media_type="application/json")

    elif format == "text":
        summary = report_gen.generate_text_summary(result)
        return JSONResponse(content={"summary": summary})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {format}")


@app.get("/api/walk-forward/visualization/{job_id}")
async def get_visualization_data(job_id: str) -> APIResponse:
    """
    Get visualization data for walk-forward results

    Args:
        job_id: Job identifier

    Returns:
        APIResponse with chart-ready visualization data
    """
    correlation_id = create_correlation_id()

    if job_id not in results:
        raise HTTPException(status_code=404, detail=f"Results for job {job_id} not found")

    result = results[job_id]

    viz_gen = VisualizationDataGenerator()
    viz_data = viz_gen.generate_all_visualization_data(result)

    return APIResponse(
        data=viz_data,
        error=None,
        correlation_id=correlation_id
    )


@app.get("/api/walk-forward/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, regex="^(pending|running|completed|failed)$"),
    limit: int = Query(50, ge=1, le=200)
) -> APIResponse:
    """
    List all walk-forward optimization jobs

    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return

    Returns:
        APIResponse with list of jobs
    """
    correlation_id = create_correlation_id()

    # Filter jobs
    filtered_jobs = list(jobs.values())

    if status:
        filtered_jobs = [j for j in filtered_jobs if j.status == status]

    # Sort by creation time (newest first)
    filtered_jobs.sort(key=lambda j: j.created_at, reverse=True)

    # Apply limit
    filtered_jobs = filtered_jobs[:limit]

    return APIResponse(
        data={
            "jobs": [j.model_dump(mode='json') for j in filtered_jobs],
            "total": len(filtered_jobs)
        },
        error=None,
        correlation_id=correlation_id
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Walk-Forward Optimization Service starting...")
    logger.info(f"Report directory: {REPORT_DIR.absolute()}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Walk-Forward Optimization Service shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
