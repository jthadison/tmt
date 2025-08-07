"""
Circuit Breaker Agent Main Application

FastAPI application providing REST API and WebSocket interfaces
for the circuit breaker agent with <100ms emergency response requirements.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

# Import agent modules
from .config import config
from .models import (
    StandardAPIResponse, EmergencyStopRequest, EmergencyStopResponse,
    BreakerStatusResponse, SystemHealth, WebSocketMessage, BreakerLevel, TriggerReason
)
from .breaker_logic import CircuitBreakerManager
from .emergency_stop import EmergencyStopManager
from .health_monitor import HealthMonitor
from .kafka_events import KafkaEventManager

# Import shared health utilities (fallback for development)
try:
    # Try proper package import first
    from agents.shared.health import HealthChecker, setup_health_endpoint
except ImportError:
    # Fallback if shared module not available yet
    HealthChecker = None
    setup_health_endpoint = lambda app, checker: None

logger = structlog.get_logger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        logger.info("WebSocket client connected", total_connections=self.connection_count)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_count -= 1
            logger.info("WebSocket client disconnected", total_connections=self.connection_count)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("Failed to send WebSocket message", error=str(e))
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global components
breaker_manager: Optional[CircuitBreakerManager] = None
emergency_stop_manager: Optional[EmergencyStopManager] = None
health_monitor: Optional[HealthMonitor] = None
kafka_manager: Optional[KafkaEventManager] = None
websocket_manager: Optional[WebSocketConnectionManager] = None
health_checker: Optional[HealthChecker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global breaker_manager, emergency_stop_manager, health_monitor, kafka_manager, websocket_manager, health_checker
    
    logger.info("Starting Circuit Breaker Agent", version=config.version)
    
    try:
        # Initialize components
        breaker_manager = CircuitBreakerManager()
        emergency_stop_manager = EmergencyStopManager(breaker_manager)
        health_monitor = HealthMonitor(breaker_manager, emergency_stop_manager)
        kafka_manager = KafkaEventManager()
        websocket_manager = WebSocketConnectionManager()
        
        if HealthChecker:
            health_checker = HealthChecker(
                service_name=config.service_name,
                version=config.version
            )
        
        # Setup Kafka event handlers
        await setup_kafka_handlers()
        
        # Connect to Kafka
        if not await kafka_manager.connect():
            logger.warning("Failed to connect to Kafka - continuing without event integration")
        
        # Start consuming health events from other agents
        if kafka_manager.is_connected:
            await kafka_manager.start_consuming([
                'agent.health.update',
                'execution.position.update',
                'market.data.update'
            ])
        
        # Setup health monitoring callbacks
        health_monitor.add_health_callback(lambda health: asyncio.create_task(
            broadcast_health_update(health)
        ))
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        logger.info("Circuit Breaker Agent startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.exception("Startup failed", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Circuit Breaker Agent")
        
        if health_monitor:
            await health_monitor.cleanup()
        if emergency_stop_manager:
            await emergency_stop_manager.cleanup()
        if kafka_manager:
            await kafka_manager.disconnect()
        
        logger.info("Circuit Breaker Agent shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Circuit Breaker Agent",
    description="Emergency stop and circuit breaker agent for adaptive trading system",
    version=config.version,
    lifespan=lifespan,
    docs_url="/api/docs" if not config.is_production else None,
    redoc_url="/api/redoc" if not config.is_production else None,
    openapi_url="/api/openapi.json" if not config.is_production else None
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not config.is_production else [config.dashboard_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if config.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", config.host]
    )

# Setup health endpoint
if HealthChecker:
    @app.on_event("startup")
    async def setup_health():
        if health_checker:
            setup_health_endpoint(app, health_checker)


async def setup_kafka_handlers():
    """Setup Kafka event handlers"""
    if not kafka_manager:
        return
    
    async def handle_agent_health(event_data: Dict[str, Any]):
        """Handle agent health update events"""
        logger.debug("Received agent health update", event_data=event_data)
        # Could update agent-specific health metrics here
    
    async def handle_position_update(event_data: Dict[str, Any]):
        """Handle position update events"""
        logger.debug("Received position update", event_data=event_data)
        # Could update position-related metrics here
    
    async def handle_market_update(event_data: Dict[str, Any]):
        """Handle market data update events"""
        logger.debug("Received market update", event_data=event_data)
        # Could update market condition metrics here
    
    kafka_manager.add_event_handler('agent_health_update', handle_agent_health)
    kafka_manager.add_event_handler('position_update', handle_position_update)
    kafka_manager.add_event_handler('market_data_update', handle_market_update)


async def broadcast_health_update(health: SystemHealth):
    """Broadcast health update to WebSocket clients"""
    if websocket_manager:
        message = WebSocketMessage(
            type="health_update",
            data=health.dict()
        )
        await websocket_manager.broadcast(message.dict())


def get_correlation_id() -> str:
    """Generate correlation ID for request tracing"""
    return str(uuid4())


# REST API Endpoints

@app.get("/api/v1/breaker/status", response_model=StandardAPIResponse)
async def get_breaker_status():
    """Get current circuit breaker status for all levels"""
    try:
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        if not breaker_manager:
            raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
        
        # Get current health metrics
        current_health = None
        if health_monitor:
            current_health = await health_monitor.run_health_check()
        
        # Get all breaker status
        status = breaker_manager.get_all_breaker_status()
        
        # Determine overall system status
        overall_status = "healthy"
        if not status['overall_healthy']:
            overall_status = "emergency_stop_active"
        elif current_health and current_health.error_rate > 0.1:
            overall_status = "degraded"
        
        response_data = BreakerStatusResponse(
            agent_breakers=status['agent_breakers'],
            account_breakers=status['account_breakers'],
            system_breaker=status['system_breaker'],
            overall_status=overall_status,
            health_metrics=current_health or SystemHealth(
                cpu_usage=0, memory_usage=0, disk_usage=0, 
                error_rate=0, response_time=0
            ),
            correlation_id=correlation_id
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Record response time for monitoring
        if health_monitor:
            health_monitor.record_response_time(response_time)
        
        return StandardAPIResponse(
            data=response_data.dict(),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.exception("Failed to get breaker status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/breaker/trigger", response_model=StandardAPIResponse)
async def trigger_emergency_stop(
    request: EmergencyStopRequest,
    background_tasks: BackgroundTasks
):
    """Trigger emergency stop with specified level and reason"""
    try:
        start_time = time.time()
        
        if not emergency_stop_manager:
            raise HTTPException(status_code=503, detail="Emergency stop manager not initialized")
        
        logger.critical(
            "Manual emergency stop requested",
            level=request.level.value,
            reason=request.reason.value,
            correlation_id=request.correlation_id,
            requested_by=request.requested_by
        )
        
        # Execute emergency stop
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        # Publish event to Kafka
        if kafka_manager and kafka_manager.is_connected:
            background_tasks.add_task(
                kafka_manager.publish_breaker_triggered,
                request.level,
                emergency_stop_manager._get_identifier_for_level(request.level),
                request.reason,
                request.details,
                request.correlation_id
            )
        
        # Broadcast to WebSocket clients
        if websocket_manager:
            background_tasks.add_task(
                websocket_manager.broadcast,
                WebSocketMessage(
                    type="emergency_stop_triggered",
                    data=response.dict(),
                    correlation_id=request.correlation_id
                ).dict()
            )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # Ensure we meet <100ms requirement for critical operations
        if execution_time > 100:
            logger.warning(
                "Emergency stop exceeded 100ms requirement",
                execution_time_ms=execution_time,
                correlation_id=request.correlation_id
            )
        
        return StandardAPIResponse(
            data=response.dict(),
            correlation_id=request.correlation_id
        )
        
    except Exception as e:
        logger.exception("Emergency stop failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/breaker/reset", response_model=StandardAPIResponse)
async def reset_circuit_breaker(
    level: BreakerLevel,
    identifier: str = "system",
    background_tasks: BackgroundTasks
):
    """Reset circuit breaker to normal state"""
    try:
        correlation_id = get_correlation_id()
        
        if not breaker_manager:
            raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
        
        success = await breaker_manager.manual_reset(level, identifier)
        
        if success:
            logger.info(
                "Circuit breaker manually reset",
                level=level.value,
                identifier=identifier,
                correlation_id=correlation_id
            )
            
            # Publish status update
            if kafka_manager and kafka_manager.is_connected:
                status = breaker_manager.get_all_breaker_status()
                background_tasks.add_task(
                    kafka_manager.publish_status_update,
                    status,
                    correlation_id
                )
        
        return StandardAPIResponse(
            data={"success": success, "level": level.value, "identifier": identifier},
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.exception("Circuit breaker reset failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/breaker/history")
async def get_breaker_history():
    """Get circuit breaker activation history"""
    # This would typically query a database
    # For now, return placeholder data
    correlation_id = get_correlation_id()
    
    return StandardAPIResponse(
        data={
            "history": [],
            "total_activations": 0,
            "last_activation": None
        },
        correlation_id=correlation_id
    )


@app.get("/api/v1/health/summary")
async def get_health_summary():
    """Get health monitoring summary"""
    try:
        correlation_id = get_correlation_id()
        
        summary = {}
        if health_monitor:
            summary = health_monitor.get_health_summary()
        
        return StandardAPIResponse(
            data=summary,
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.exception("Failed to get health summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws/breaker/status")
async def websocket_breaker_status(websocket: WebSocket):
    """WebSocket endpoint for real-time breaker status updates"""
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial status
        if breaker_manager:
            status = breaker_manager.get_all_breaker_status()
            current_health = None
            if health_monitor:
                current_health = health_monitor.get_current_health()
            
            initial_message = WebSocketMessage(
                type="initial_status",
                data={
                    "breaker_status": status,
                    "health_metrics": current_health.dict() if current_health else None
                }
            )
            await websocket.send_text(json.dumps(initial_message.dict()))
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (heartbeat, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=config.websocket_heartbeat_interval
                )
                
                # Handle client message (could be heartbeat, subscription changes, etc.)
                try:
                    message = json.loads(data)
                    if message.get('type') == 'ping':
                        await websocket.send_text(json.dumps({
                            'type': 'pong',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }))
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from WebSocket client")
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.exception("WebSocket error", error=str(e))
    finally:
        websocket_manager.disconnect(websocket)


# Development/Testing endpoints (non-production only)
if not config.is_production:
    
    @app.post("/dev/simulate-load")
    async def simulate_high_load(duration_seconds: int = 60):
        """Simulate high system load for testing"""
        if health_monitor:
            await health_monitor.simulate_high_load(duration_seconds)
        return {"message": f"Load simulation started for {duration_seconds} seconds"}
    
    @app.post("/dev/trigger-test-condition")
    async def trigger_test_condition(condition_type: str):
        """Trigger test conditions for development"""
        correlation_id = get_correlation_id()
        
        if condition_type == "high_error_rate" and health_monitor:
            for i in range(10):
                health_monitor.record_error("test_error")
        elif condition_type == "slow_response" and health_monitor:
            for i in range(5):
                health_monitor.record_response_time(500 + i * 100)
        
        return StandardAPIResponse(
            data={"condition_triggered": condition_type},
            correlation_id=correlation_id
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower()
    )