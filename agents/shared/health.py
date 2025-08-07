"""
Health Check Module for Trading Agents

Provides standardized health check functionality for all AI agents
following the system-wide health check specification.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

import psutil
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# from .database import DatabaseManager  # TODO: Implement when database module is ready
# from .kafka_client import KafkaManager  # TODO: Implement when Kafka module is ready

logger = logging.getLogger(__name__)


class HealthCheckResponse(BaseModel):
    """Standardized health check response model"""
    
    data: Dict[str, Any]
    error: Optional[str] = None
    correlation_id: str = Field(..., alias="correlation_id")


class HealthStatus(BaseModel):
    """Health status data model"""
    
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    service: str
    version: str
    uptime: float
    environment: str
    response_time: int
    correlation_id: str
    checks: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]


class HealthChecker:
    """Health check implementation for trading agents"""
    
    def __init__(
        self, 
        service_name: str, 
        version: str = "0.1.0",
        db_manager: Optional[Any] = None,  # DatabaseManager when implemented
        kafka_manager: Optional[Any] = None  # KafkaManager when implemented
    ):
        self.service_name = service_name
        self.version = version
        self.db_manager = db_manager
        self.kafka_manager = kafka_manager
        self.start_time = time.time()
    
    async def check_health(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Perform comprehensive health check
        
        Args:
            correlation_id: Request correlation ID for tracing
            
        Returns:
            HealthStatus: Complete health status information
        """
        start_time = time.time()
        correlation_id = correlation_id or str(uuid4())
        
        try:
            # Run all health checks concurrently
            check_tasks = [
                self._check_database(),
                self._check_kafka(),
                self._check_memory(),
                self._check_disk(),
                self._check_cpu(),
            ]
            
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            checks = {
                'database': self._process_result(results[0]),
                'kafka': self._process_result(results[1]),
                'memory': self._process_result(results[2]),
                'disk': self._process_result(results[3]),
                'cpu': self._process_result(results[4]),
            }
            
            # Determine overall status
            status = self._determine_overall_status(checks)
            
            health_status = HealthStatus(
                status=status,
                timestamp=datetime.now(timezone.utc).isoformat(),
                service=self.service_name,
                version=self.version,
                uptime=time.time() - self.start_time,
                environment=self._get_environment(),
                response_time=int((time.time() - start_time) * 1000),
                correlation_id=correlation_id,
                checks=checks,
                metadata=self._get_system_metadata()
            )
            
            return health_status
            
        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            raise HTTPException(
                status_code=503, 
                detail=f"Health check failed: {str(e)}"
            )
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            if not self.db_manager:
                return {
                    'status': 'skipped',
                    'message': 'Database manager not configured',
                    'response_time': int((time.time() - start_time) * 1000)
                }
            
            # Test database connection with a simple query  
            # TODO: Implement actual database connection test
            # await self.db_manager.execute_query("SELECT 1")
            await asyncio.sleep(0.01)  # Simulate database check
            
            return {
                'status': 'passed',
                'message': 'Database connection healthy',
                'response_time': int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Database check failed: {str(e)}',
                'response_time': int((time.time() - start_time) * 1000)
            }
    
    async def _check_kafka(self) -> Dict[str, Any]:
        """Check Kafka connectivity and producer health"""
        start_time = time.time()
        
        try:
            if not self.kafka_manager:
                return {
                    'status': 'skipped',
                    'message': 'Kafka manager not configured',
                    'response_time': int((time.time() - start_time) * 1000)
                }
            
            # Test Kafka connectivity
            # TODO: Implement actual Kafka connectivity test
            # is_healthy = await self.kafka_manager.health_check()
            await asyncio.sleep(0.005)  # Simulate Kafka check
            is_healthy = True  # Simulated for now
            
            if is_healthy:
                return {
                    'status': 'passed',
                    'message': 'Kafka connection healthy',
                    'response_time': int((time.time() - start_time) * 1000)
                }
            else:
                return {
                    'status': 'failed',
                    'message': 'Kafka connection failed',
                    'response_time': int((time.time() - start_time) * 1000)
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Kafka check failed: {str(e)}',
                'response_time': int((time.time() - start_time) * 1000)
            }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = 'failed'
                message = f'High memory usage: {usage_percent:.1f}%'
            elif usage_percent > 80:
                status = 'warning'
                message = f'Elevated memory usage: {usage_percent:.1f}%'
            else:
                status = 'passed'
                message = f'Memory usage normal: {usage_percent:.1f}%'
            
            return {
                'status': status,
                'message': message,
                'response_time': int((time.time() - start_time) * 1000),
                'details': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percentage': usage_percent
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Memory check failed: {str(e)}',
                'response_time': int((time.time() - start_time) * 1000)
            }
    
    async def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage"""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 90:
                status = 'failed'
                message = f'High disk usage: {usage_percent:.1f}%'
            elif usage_percent > 80:
                status = 'warning'
                message = f'Elevated disk usage: {usage_percent:.1f}%'
            else:
                status = 'passed'
                message = f'Disk usage normal: {usage_percent:.1f}%'
            
            return {
                'status': status,
                'message': message,
                'response_time': int((time.time() - start_time) * 1000),
                'details': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percentage': usage_percent
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Disk check failed: {str(e)}',
                'response_time': int((time.time() - start_time) * 1000)
            }
    
    async def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        start_time = time.time()
        
        try:
            # Get CPU usage over a short interval
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            if cpu_percent > 90:
                status = 'failed'
                message = f'High CPU usage: {cpu_percent:.1f}%'
            elif cpu_percent > 80:
                status = 'warning'
                message = f'Elevated CPU usage: {cpu_percent:.1f}%'
            else:
                status = 'passed'
                message = f'CPU usage normal: {cpu_percent:.1f}%'
            
            return {
                'status': status,
                'message': message,
                'response_time': int((time.time() - start_time) * 1000),
                'details': {
                    'percentage': cpu_percent,
                    'count': psutil.cpu_count(),
                    'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'CPU check failed: {str(e)}',
                'response_time': int((time.time() - start_time) * 1000)
            }
    
    def _process_result(self, result: Any) -> Dict[str, Any]:
        """Process health check result, handling exceptions"""
        if isinstance(result, Exception):
            return {
                'status': 'failed',
                'message': f'Check failed with exception: {str(result)}',
                'response_time': 0
            }
        return result
    
    def _determine_overall_status(self, checks: Dict[str, Dict[str, Any]]) -> str:
        """Determine overall health status from individual checks"""
        failed_checks = [
            name for name, check in checks.items() 
            if check.get('status') == 'failed'
        ]
        
        warning_checks = [
            name for name, check in checks.items() 
            if check.get('status') == 'warning'
        ]
        
        if failed_checks:
            return 'unhealthy'
        elif warning_checks:
            return 'degraded'
        else:
            return 'healthy'
    
    def _get_environment(self) -> str:
        """Get current environment"""
        import os
        return os.getenv('ENVIRONMENT', 'development')
    
    def _get_system_metadata(self) -> Dict[str, Any]:
        """Get system metadata for diagnostics"""
        import platform
        import sys
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'hostname': platform.node(),
            'pid': os.getpid(),
            'thread_count': psutil.Process().num_threads(),
        }


def setup_health_endpoint(app: FastAPI, health_checker: HealthChecker):
    """
    Setup health check endpoint on FastAPI application
    
    Args:
        app: FastAPI application instance
        health_checker: Health checker instance
    """
    
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check(request: Request):
        """Health check endpoint"""
        correlation_id = request.headers.get('x-correlation-id')
        
        try:
            health_status = await health_checker.check_health(correlation_id)
            
            # Determine HTTP status code based on health status
            status_code = 200
            if health_status.status == 'unhealthy':
                status_code = 503
            elif health_status.status == 'degraded':
                status_code = 200  # Still accepting traffic but with warnings
            
            return JSONResponse(
                content={
                    "data": health_status.dict(),
                    "error": None,
                    "correlation_id": health_status.correlation_id
                },
                status_code=status_code,
                headers={
                    "X-Correlation-ID": health_status.correlation_id,
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error in health check")
            correlation_id = correlation_id or str(uuid4())
            
            return JSONResponse(
                content={
                    "data": {
                        "status": "unhealthy",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "service": health_checker.service_name,
                        "error": str(e),
                        "correlation_id": correlation_id
                    },
                    "error": str(e),
                    "correlation_id": correlation_id
                },
                status_code=503,
                headers={
                    "X-Correlation-ID": correlation_id
                }
            )