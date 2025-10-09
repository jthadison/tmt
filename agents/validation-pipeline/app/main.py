"""
Validation Pipeline REST API - Story 11.7, Task 8

FastAPI service for automated parameter validation with async job support.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .pipeline import ValidationPipeline
from .models import (
    ValidationReport, ValidationJobStatus, ValidationStatus,
    MonteCarloConfig
)
from .report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Parameter Validation Pipeline",
    description="Automated validation pipeline for trading parameter configurations",
    version="1.0.0"
)

# In-memory job store (in production, use Redis or database)
job_store: Dict[str, ValidationJobStatus] = {}


class ValidationRequest(BaseModel):
    """Request to validate parameter configuration"""
    config_file: str
    output_file: Optional[str] = None
    monte_carlo_runs: Optional[int] = 1000
    parallel_workers: Optional[int] = 4


class ValidationJobResponse(BaseModel):
    """Response containing job ID for async validation"""
    job_id: str
    status: str
    message: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "validation-pipeline",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/validation/run", response_model=ValidationJobResponse)
async def run_validation(
    request: ValidationRequest,
    background_tasks: BackgroundTasks
) -> ValidationJobResponse:
    """
    Start asynchronous parameter validation

    Returns job ID for status polling.
    """
    # Create job ID
    job_id = str(uuid.uuid4())

    # Create job status
    job_status = ValidationJobStatus(
        job_id=job_id,
        status=ValidationStatus.IN_PROGRESS,
        progress_pct=0.0,
        current_step="Initializing validation pipeline",
        started_at=datetime.utcnow()
    )

    # Store job status
    job_store[job_id] = job_status

    logger.info(f"Starting validation job {job_id} for {request.config_file}")

    # Run validation in background
    background_tasks.add_task(
        run_validation_job,
        job_id,
        request.config_file,
        request.output_file,
        request.monte_carlo_runs,
        request.parallel_workers
    )

    return ValidationJobResponse(
        job_id=job_id,
        status="IN_PROGRESS",
        message=f"Validation started. Poll /api/validation/status/{job_id} for results."
    )


@app.get("/api/validation/status/{job_id}")
async def get_validation_status(job_id: str) -> ValidationJobStatus:
    """
    Get status of validation job

    Args:
        job_id: Job ID from run_validation

    Returns:
        Current job status
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job_store[job_id]


@app.post("/api/validation/run-sync")
async def run_validation_sync(request: ValidationRequest) -> ValidationReport:
    """
    Run synchronous parameter validation

    Blocks until validation completes. Use for smaller validations
    or when immediate results are needed.
    """
    logger.info(f"Starting synchronous validation for {request.config_file}")

    try:
        # Create Monte Carlo config
        mc_config = MonteCarloConfig(
            num_runs=request.monte_carlo_runs or 1000,
            parallel_workers=request.parallel_workers or 4
        )

        # Create pipeline
        pipeline = ValidationPipeline(monte_carlo_config=mc_config)

        # Run validation
        report = await pipeline.validate_parameter_change(
            request.config_file,
            request.output_file
        )

        return report

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Config file not found: {request.config_file}")
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/api/validation/report/{job_id}/markdown")
async def get_markdown_report(job_id: str) -> JSONResponse:
    """
    Get validation report in Markdown format

    Useful for GitHub PR comments.
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = job_store[job_id]

    if job.status == ValidationStatus.IN_PROGRESS:
        raise HTTPException(status_code=425, detail="Validation still in progress")

    if job.result is None:
        raise HTTPException(status_code=404, detail="No report available")

    # Generate Markdown report
    report_gen = ReportGenerator()
    markdown = report_gen.generate_markdown_report(job.result)

    return JSONResponse(
        content={"markdown": markdown},
        media_type="application/json"
    )


async def run_validation_job(
    job_id: str,
    config_file: str,
    output_file: Optional[str],
    monte_carlo_runs: int,
    parallel_workers: int
) -> None:
    """
    Background task to run validation

    Updates job status as validation progresses.
    """
    try:
        # Update status
        job_store[job_id].current_step = "Creating validation pipeline"
        job_store[job_id].progress_pct = 10.0

        # Create Monte Carlo config
        mc_config = MonteCarloConfig(
            num_runs=monte_carlo_runs,
            parallel_workers=parallel_workers
        )

        # Create pipeline
        pipeline = ValidationPipeline(monte_carlo_config=mc_config)

        # Run validation with progress updates
        job_store[job_id].current_step = "Running schema validation"
        job_store[job_id].progress_pct = 20.0

        report = await pipeline.validate_parameter_change(config_file, output_file)

        # Update job status with results
        job_store[job_id].status = report.status
        job_store[job_id].progress_pct = 100.0
        job_store[job_id].current_step = "Completed"
        job_store[job_id].completed_at = datetime.utcnow()
        job_store[job_id].result = report

        logger.info(f"Validation job {job_id} completed - Status: {report.status.value}")

    except Exception as e:
        logger.error(f"Validation job {job_id} failed: {e}", exc_info=True)

        # Update job status with error
        job_store[job_id].status = ValidationStatus.FAILED
        job_store[job_id].progress_pct = 0.0
        job_store[job_id].current_step = "Failed"
        job_store[job_id].completed_at = datetime.utcnow()
        job_store[job_id].error_message = str(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
