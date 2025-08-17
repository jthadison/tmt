"""
Main Broker Integration Service
Story 8.1: Complete OANDA Broker Authentication & Connection Management
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from credential_manager import OandaCredentialManager, CredentialValidationError, VaultConnectionError
from oanda_auth_handler import OandaAuthHandler, AuthenticationError
from connection_pool import OandaConnectionPool
from reconnection_manager import OandaReconnectionManager
from session_manager import SessionManager
from dashboard_widget import ConnectionStatusWidget

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Prometheus metrics
REQUEST_COUNT = Counter('broker_requests_total', 'Total broker API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('broker_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('broker_active_connections', 'Number of active broker connections')
AUTHENTICATION_ATTEMPTS = Counter('broker_auth_attempts_total', 'Authentication attempts', ['status'])
SESSION_COUNT = Gauge('broker_active_sessions', 'Number of active sessions')
ERROR_COUNT = Counter('broker_errors_total', 'Total broker errors', ['error_type'])
RECONNECTION_ATTEMPTS = Counter('broker_reconnection_attempts_total', 'Reconnection attempts', ['status'])

# Pydantic models for API
class CredentialRequest(BaseModel):
    user_id: str
    api_key: str
    account_id: str
    environment: str  # 'practice' or 'live'

class AuthenticationRequest(BaseModel):
    user_id: str
    account_id: str
    environment: str

class SessionCreateRequest(BaseModel):
    user_id: str
    account_id: str
    environment: str
    persist: bool = True
    auto_refresh: bool = True

# Global components
credential_manager: Optional[OandaCredentialManager] = None
auth_handler: Optional[OandaAuthHandler] = None
connection_pool: Optional[OandaConnectionPool] = None
reconnection_manager: Optional[OandaReconnectionManager] = None
session_manager: Optional[SessionManager] = None
dashboard_widget: Optional[ConnectionStatusWidget] = None

async def initialize_components():
    """Initialize all broker integration components"""
    global credential_manager, auth_handler, connection_pool, reconnection_manager, session_manager, dashboard_widget
    
    logger.info("Initializing OANDA Broker Integration components...")
    
    # Configuration from environment
    vault_url = os.getenv('VAULT_URL', 'http://localhost:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'dev-token')
    
    # Initialize credential manager
    credential_manager = OandaCredentialManager(vault_url, vault_token)
    
    # Initialize authentication handler
    auth_handler = OandaAuthHandler(credential_manager)
    
    # Initialize connection pool
    connection_pool = OandaConnectionPool(pool_size=20)
    await connection_pool.initialize()
    
    # Initialize reconnection manager
    reconnection_manager = OandaReconnectionManager(
        max_retries=10,
        target_reconnection_time=5.0
    )
    
    # Initialize session manager
    session_manager = SessionManager(
        auth_handler=auth_handler,
        persistence_file="data/oanda_sessions.pkl"
    )
    await session_manager.start()
    
    # Initialize dashboard widget
    dashboard_widget = ConnectionStatusWidget(
        auth_handler=auth_handler,
        connection_pool=connection_pool,
        reconnection_manager=reconnection_manager
    )
    await dashboard_widget.start()
    
    logger.info("All components initialized successfully")

async def shutdown_components():
    """Gracefully shutdown all components"""
    global credential_manager, auth_handler, connection_pool, reconnection_manager, session_manager, dashboard_widget
    
    logger.info("Shutting down OANDA Broker Integration components...")
    
    if dashboard_widget:
        await dashboard_widget.stop()
    
    if session_manager:
        await session_manager.stop()
    
    if reconnection_manager:
        await reconnection_manager.shutdown()
    
    if connection_pool:
        await connection_pool.close()
    
    logger.info("All components shut down gracefully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    app.state.start_time = datetime.utcnow()
    await initialize_components()
    yield
    # Shutdown
    await shutdown_components()

# FastAPI application
app = FastAPI(
    title="OANDA Broker Integration",
    description="Story 8.1: Broker Authentication & Connection Management",
    version="1.0.0",
    lifespan=lifespan
)

# Dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple auth dependency - replace with real auth in production"""
    # For demo purposes, extract user_id from token
    return credentials.credentials

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes liveness probe"""
    try:
        health_status = {}
        overall_status = 'healthy'
        
        # Check credential manager
        if credential_manager:
            try:
                health_status['credential_manager'] = credential_manager.health_check()
            except Exception as e:
                health_status['credential_manager'] = {'status': 'unhealthy', 'error': str(e)}
                overall_status = 'degraded'
        
        # Check connection pool
        if connection_pool:
            try:
                pool_stats = connection_pool.get_pool_stats()
                health_status['connection_pool'] = {
                    'status': 'healthy',
                    'active_connections': pool_stats['active_connections'],
                    'pool_size': pool_stats['pool_size']
                }
                # Mark as unhealthy if no connections available
                if pool_stats['available_connections'] == 0:
                    health_status['connection_pool']['status'] = 'warning'
                    overall_status = 'degraded'
            except Exception as e:
                health_status['connection_pool'] = {'status': 'unhealthy', 'error': str(e)}
                overall_status = 'unhealthy'
        
        # Check reconnection manager
        if reconnection_manager:
            try:
                health_status['reconnection_manager'] = reconnection_manager.get_system_health()
                if not health_status['reconnection_manager'].get('operational', True):
                    overall_status = 'degraded'
            except Exception as e:
                health_status['reconnection_manager'] = {'status': 'unhealthy', 'error': str(e)}
                overall_status = 'degraded'
        
        # Check session manager
        if session_manager:
            try:
                session_stats = session_manager.get_session_statistics()
                health_status['session_manager'] = {
                    'status': 'healthy',
                    'total_sessions': session_stats['total_sessions'],
                    'active_sessions': session_stats['session_states']['active']
                }
            except Exception as e:
                health_status['session_manager'] = {'status': 'unhealthy', 'error': str(e)}
                overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': health_status,
            'uptime_seconds': (datetime.utcnow() - app.state.start_time).total_seconds() if hasattr(app.state, 'start_time') else 0
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe"""
    try:
        # Check if all critical components are ready
        ready_status = {}
        is_ready = True
        
        # Critical: Credential manager must be functional
        if not credential_manager:
            ready_status['credential_manager'] = {'ready': False, 'reason': 'Not initialized'}
            is_ready = False
        else:
            try:
                health = credential_manager.health_check()
                if health.get('vault_connected', False):
                    ready_status['credential_manager'] = {'ready': True}
                else:
                    ready_status['credential_manager'] = {'ready': False, 'reason': 'Vault not connected'}
                    is_ready = False
            except Exception as e:
                ready_status['credential_manager'] = {'ready': False, 'reason': str(e)}
                is_ready = False
        
        # Critical: Connection pool must be available
        if not connection_pool:
            ready_status['connection_pool'] = {'ready': False, 'reason': 'Not initialized'}
            is_ready = False
        else:
            try:
                pool_stats = connection_pool.get_pool_stats()
                if pool_stats['available_connections'] > 0:
                    ready_status['connection_pool'] = {'ready': True}
                else:
                    ready_status['connection_pool'] = {'ready': False, 'reason': 'No available connections'}
                    is_ready = False
            except Exception as e:
                ready_status['connection_pool'] = {'ready': False, 'reason': str(e)}
                is_ready = False
        
        # Non-critical: Auth handler should be ready but service can start without it
        if auth_handler:
            ready_status['auth_handler'] = {'ready': True}
        else:
            ready_status['auth_handler'] = {'ready': False, 'reason': 'Not initialized'}
        
        status_code = 200 if is_ready else 503
        
        return {
            'ready': is_ready,
            'timestamp': datetime.utcnow().isoformat(),
            'components': ready_status
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            'ready': False,
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update current metrics before serving
        if connection_pool:
            pool_stats = connection_pool.get_pool_stats()
            ACTIVE_CONNECTIONS.set(pool_stats['active_connections'])
        
        if session_manager:
            session_stats = session_manager.get_session_statistics()
            SESSION_COUNT.set(session_stats['session_states']['active'])
        
        # Generate Prometheus format
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        ERROR_COUNT.labels(error_type='metrics_generation').inc()
        raise HTTPException(status_code=500, detail='Failed to generate metrics')

@app.post("/api/credentials/store")
async def store_credentials(request: CredentialRequest, user: str = Depends(get_current_user)):
    """Store OANDA credentials securely"""
    try:
        credentials = {
            'api_key': request.api_key,
            'account_id': request.account_id,
            'environment': request.environment
        }
        
        success = await credential_manager.store_credentials(request.user_id, credentials)
        
        if success:
            return {'message': 'Credentials stored successfully'}
        else:
            raise HTTPException(status_code=500, detail='Failed to store credentials')
            
    except CredentialValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing credentials: {e}")
        raise HTTPException(status_code=500, detail='Internal server error')

@app.post("/api/auth/authenticate")
async def authenticate(request: AuthenticationRequest, user: str = Depends(get_current_user)):
    """Authenticate user with OANDA account"""
    try:
        context = await auth_handler.authenticate_user(
            request.user_id,
            request.account_id,
            request.environment
        )
        
        return {
            'message': 'Authentication successful',
            'account_id': context.account_id,
            'environment': context.environment.value,
            'authenticated_at': context.authenticated_at.isoformat()
        }
        
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail='Authentication failed')

@app.post("/api/sessions/create")
async def create_session(request: SessionCreateRequest, user: str = Depends(get_current_user)):
    """Create new session"""
    try:
        session_id = await session_manager.create_session(
            user_id=request.user_id,
            account_id=request.account_id,
            environment=request.environment,
            persist=request.persist,
            auto_refresh=request.auto_refresh
        )
        
        return {
            'session_id': session_id,
            'message': 'Session created successfully'
        }
        
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(status_code=500, detail='Failed to create session')

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, user: str = Depends(get_current_user)):
    """Get session information"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    return {
        'session_id': session.session_id,
        'user_id': session.user_id,
        'account_id': session.account_id,
        'environment': session.environment,
        'state': session.state.value,
        'created_at': session.metrics.created_at.isoformat(),
        'last_activity': session.metrics.last_activity.isoformat(),
        'metrics': {
            'total_requests': session.metrics.total_requests,
            'error_rate': session.metrics.error_rate,
            'average_response_time': session.metrics.average_response_time
        }
    }

@app.delete("/api/sessions/{session_id}")
async def terminate_session(session_id: str, user: str = Depends(get_current_user)):
    """Terminate session"""
    success = await session_manager.terminate_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail='Session not found')
    
    return {'message': 'Session terminated successfully'}

@app.get("/api/users/{user_id}/accounts")
async def get_user_accounts(user_id: str, user: str = Depends(get_current_user)):
    """Get all OANDA accounts for user"""
    try:
        accounts = await auth_handler.get_user_accounts(user_id)
        return {'accounts': accounts}
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail='Failed to fetch accounts')

@app.post("/api/connections/{connection_id}/reconnect")
async def trigger_reconnection(connection_id: str, user: str = Depends(get_current_user)):
    """Manually trigger reconnection"""
    success = await reconnection_manager.trigger_manual_reconnection(connection_id)
    if success:
        return {'message': 'Reconnection initiated'}
    else:
        raise HTTPException(status_code=400, detail='Failed to initiate reconnection')

@app.get("/api/dashboard/status")
async def get_dashboard_status(user: str = Depends(get_current_user)):
    """Get complete dashboard status"""
    try:
        data = await dashboard_widget.get_dashboard_data()
        return data
    except Exception as e:
        logger.error(f"Error getting dashboard status: {e}")
        raise HTTPException(status_code=500, detail='Failed to get dashboard status')

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    
    try:
        await dashboard_widget.add_websocket_client(websocket)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()  # Just to detect disconnection
            
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        await dashboard_widget.remove_websocket_client(websocket)

@app.get("/api/stats/system")
async def get_system_stats(user: str = Depends(get_current_user)):
    """Get comprehensive system statistics"""
    stats = {}
    
    if connection_pool:
        stats['connection_pool'] = connection_pool.get_pool_stats()
    
    if reconnection_manager:
        stats['reconnection_manager'] = reconnection_manager.get_system_health()
    
    if session_manager:
        stats['session_manager'] = session_manager.get_session_statistics()
    
    if auth_handler:
        stats['auth_handler'] = auth_handler.get_session_stats()
    
    return stats

# Connection testing utilities
async def test_connection_callback(account_id: str, api_key: str, base_url: str):
    """Test connection callback for reconnection manager"""
    async with connection_pool.acquire(account_id, api_key, base_url) as conn:
        try:
            url = f"{base_url}/v3/accounts/{account_id}"
            async with conn.session.get(url, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

# Demo and testing endpoints
@app.post("/api/demo/setup")
async def setup_demo(user: str = Depends(get_current_user)):
    """Set up demo environment with test credentials"""
    # This would be used for development/testing
    demo_credentials = {
        'api_key': 'demo-api-key',
        'account_id': '101-001-12345678-001', 
        'environment': 'practice'
    }
    
    try:
        # Note: In real implementation, this would use actual OANDA practice account credentials
        await credential_manager.store_credentials('demo-user', demo_credentials)
        session_id = await session_manager.create_session(
            'demo-user', 
            demo_credentials['account_id'],
            demo_credentials['environment']
        )
        
        return {
            'message': 'Demo environment set up successfully',
            'user_id': 'demo-user',
            'session_id': session_id
        }
        
    except Exception as e:
        logger.error(f"Demo setup error: {e}")
        raise HTTPException(status_code=500, detail='Demo setup failed')

if __name__ == "__main__":
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )