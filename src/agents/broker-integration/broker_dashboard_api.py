"""
Broker Integration Dashboard API
Provides unified API for managing multiple broker accounts and aggregating data
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# Import existing broker components
from broker_factory import BrokerFactory
from broker_adapter import BrokerAdapter, BrokerCapability
from account_manager import OandaAccountManager
from performance_metrics import BrokerPerformanceTracker
from connection_pool import ConnectionHealthMonitor
from pl_analytics import PLAnalyticsEngine
from audit_trail import AuditTrailManager

logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class BrokerAccount:
    """Unified broker account representation"""
    id: str
    broker_name: str
    account_type: str  # 'live' or 'demo'
    display_name: str
    balance: Decimal
    equity: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    margin_used: Decimal
    margin_available: Decimal
    connection_status: ConnectionStatus
    last_update: datetime
    capabilities: List[str]
    metrics: Dict[str, Any]
    currency: str = "USD"
    logo_url: str = ""

@dataclass
class AggregateData:
    """Aggregated data across all broker accounts"""
    total_balance: Decimal
    total_equity: Decimal
    total_unrealized_pl: Decimal
    total_realized_pl: Decimal
    total_margin_used: Decimal
    total_margin_available: Decimal
    account_count: int
    connected_count: int
    best_performer: Optional[str]
    worst_performer: Optional[str]
    daily_pl: Decimal
    weekly_pl: Decimal
    monthly_pl: Decimal
    last_update: datetime

@dataclass
class BrokerPerformanceMetrics:
    """Performance metrics for a broker"""
    avg_latency_ms: float
    fill_quality_score: float
    uptime_percentage: float
    total_trades: int
    successful_trades: int
    failed_trades: int
    avg_slippage_pips: float
    connection_stability: float

class BrokerDashboardManager:
    """Manages multiple broker connections and aggregates data"""
    
    def __init__(self):
        self.broker_factory = BrokerFactory()
        self.broker_accounts: Dict[str, BrokerAccount] = {}
        self.broker_adapters: Dict[str, BrokerAdapter] = {}
        self.performance_tracker = BrokerPerformanceTracker()
        self.health_monitor = ConnectionHealthMonitor()
        self.analytics_engine = PLAnalyticsEngine()
        self.audit_trail = AuditTrailManager()
        self.active_connections: List[WebSocket] = []
        self.update_interval = 5  # seconds
        self._running = False
        
    async def initialize(self):
        """Initialize the dashboard manager"""
        logger.info("Initializing Broker Dashboard Manager")
        
        # Register available brokers
        self.broker_factory.register_adapter("oanda", "OandaBrokerAdapter")
        self.broker_factory.register_adapter("interactive_brokers", "IBBrokerAdapter")
        self.broker_factory.register_adapter("alpaca", "AlpacaBrokerAdapter")
        
        # Load existing broker configurations
        await self._load_broker_configurations()
        
        # Start background monitoring
        self._running = True
        asyncio.create_task(self._monitor_brokers())
        
    async def shutdown(self):
        """Shutdown the dashboard manager"""
        logger.info("Shutting down Broker Dashboard Manager")
        self._running = False
        
        # Disconnect all brokers
        for adapter in self.broker_adapters.values():
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting broker adapter: {e}")
        
        # Close WebSocket connections
        for ws in self.active_connections:
            try:
                await ws.close()
            except Exception:
                pass
    
    async def add_broker_account(self, broker_config: Dict[str, Any]) -> str:
        """Add a new broker account"""
        try:
            broker_name = broker_config["broker_name"]
            account_id = broker_config.get("account_id", f"{broker_name}_{len(self.broker_accounts)}")
            
            # Create broker adapter
            adapter = await self.broker_factory.create_adapter(broker_name, broker_config)
            
            # Get account information
            account_summary = await adapter.get_account_summary()
            
            # Create broker account record
            broker_account = BrokerAccount(
                id=account_id,
                broker_name=broker_name,
                account_type=broker_config.get("account_type", "demo"),
                display_name=broker_config.get("display_name", f"{broker_name} - {account_id}"),
                balance=account_summary.balance,
                equity=account_summary.equity,
                unrealized_pl=account_summary.unrealized_pl,
                realized_pl=account_summary.realized_pl,
                margin_used=account_summary.margin_used,
                margin_available=account_summary.margin_available,
                connection_status=ConnectionStatus.CONNECTED,
                last_update=datetime.utcnow(),
                capabilities=[cap.value for cap in adapter.capabilities],
                metrics={},
                currency=account_summary.currency,
                logo_url=f"/assets/logos/{broker_name}.png"
            )
            
            # Store references
            self.broker_accounts[account_id] = broker_account
            self.broker_adapters[account_id] = adapter
            
            # Start monitoring this broker
            await self.health_monitor.add_broker(account_id, adapter)
            
            logger.info(f"Added broker account: {account_id} ({broker_name})")
            
            # Notify connected clients
            await self._broadcast_broker_update(account_id, broker_account)
            
            return account_id
            
        except Exception as e:
            logger.error(f"Failed to add broker account: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to add broker account: {str(e)}")
    
    async def remove_broker_account(self, account_id: str) -> bool:
        """Remove a broker account"""
        try:
            if account_id not in self.broker_accounts:
                raise HTTPException(status_code=404, detail="Broker account not found")
            
            # Disconnect adapter
            if account_id in self.broker_adapters:
                await self.broker_adapters[account_id].disconnect()
                del self.broker_adapters[account_id]
            
            # Remove from monitoring
            await self.health_monitor.remove_broker(account_id)
            
            # Remove account record
            del self.broker_accounts[account_id]
            
            logger.info(f"Removed broker account: {account_id}")
            
            # Notify connected clients
            await self._broadcast_account_removed(account_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove broker account {account_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to remove broker account: {str(e)}")
    
    async def reconnect_broker(self, account_id: str) -> bool:
        """Reconnect a broker account"""
        try:
            if account_id not in self.broker_accounts:
                raise HTTPException(status_code=404, detail="Broker account not found")
            
            # Update status to reconnecting
            self.broker_accounts[account_id].connection_status = ConnectionStatus.RECONNECTING
            await self._broadcast_broker_update(account_id, self.broker_accounts[account_id])
            
            # Attempt reconnection
            adapter = self.broker_adapters.get(account_id)
            if adapter:
                success = await adapter.reconnect()
                
                if success:
                    self.broker_accounts[account_id].connection_status = ConnectionStatus.CONNECTED
                    logger.info(f"Successfully reconnected broker: {account_id}")
                else:
                    self.broker_accounts[account_id].connection_status = ConnectionStatus.ERROR
                    logger.error(f"Failed to reconnect broker: {account_id}")
                
                await self._broadcast_broker_update(account_id, self.broker_accounts[account_id])
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error reconnecting broker {account_id}: {e}")
            self.broker_accounts[account_id].connection_status = ConnectionStatus.ERROR
            await self._broadcast_broker_update(account_id, self.broker_accounts[account_id])
            return False
    
    async def get_broker_accounts(self) -> List[BrokerAccount]:
        """Get all broker accounts"""
        return list(self.broker_accounts.values())
    
    async def get_aggregate_data(self) -> AggregateData:
        """Calculate aggregate data across all accounts"""
        accounts = list(self.broker_accounts.values())
        
        if not accounts:
            return AggregateData(
                total_balance=Decimal('0'),
                total_equity=Decimal('0'),
                total_unrealized_pl=Decimal('0'),
                total_realized_pl=Decimal('0'),
                total_margin_used=Decimal('0'),
                total_margin_available=Decimal('0'),
                account_count=0,
                connected_count=0,
                best_performer=None,
                worst_performer=None,
                daily_pl=Decimal('0'),
                weekly_pl=Decimal('0'),
                monthly_pl=Decimal('0'),
                last_update=datetime.utcnow()
            )
        
        # Calculate totals
        total_balance = sum(acc.balance for acc in accounts)
        total_equity = sum(acc.equity for acc in accounts)
        total_unrealized_pl = sum(acc.unrealized_pl for acc in accounts)
        total_realized_pl = sum(acc.realized_pl for acc in accounts)
        total_margin_used = sum(acc.margin_used for acc in accounts)
        total_margin_available = sum(acc.margin_available for acc in accounts)
        
        # Count connections
        connected_count = sum(1 for acc in accounts if acc.connection_status == ConnectionStatus.CONNECTED)
        
        # Find best/worst performers
        best_performer = max(accounts, key=lambda x: x.unrealized_pl).id if accounts else None
        worst_performer = min(accounts, key=lambda x: x.unrealized_pl).id if accounts else None
        
        # Calculate period P&L (simplified for now)
        daily_pl = total_unrealized_pl  # This would be calculated from historical data
        weekly_pl = total_unrealized_pl
        monthly_pl = total_unrealized_pl
        
        return AggregateData(
            total_balance=total_balance,
            total_equity=total_equity,
            total_unrealized_pl=total_unrealized_pl,
            total_realized_pl=total_realized_pl,
            total_margin_used=total_margin_used,
            total_margin_available=total_margin_available,
            account_count=len(accounts),
            connected_count=connected_count,
            best_performer=best_performer,
            worst_performer=worst_performer,
            daily_pl=daily_pl,
            weekly_pl=weekly_pl,
            monthly_pl=monthly_pl,
            last_update=datetime.utcnow()
        )
    
    async def get_broker_performance(self, account_id: str) -> BrokerPerformanceMetrics:
        """Get performance metrics for a specific broker"""
        if account_id not in self.broker_accounts:
            raise HTTPException(status_code=404, detail="Broker account not found")
        
        # Get metrics from performance tracker
        metrics = await self.performance_tracker.get_broker_metrics(account_id)
        
        return BrokerPerformanceMetrics(
            avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
            fill_quality_score=metrics.get("fill_quality_score", 100.0),
            uptime_percentage=metrics.get("uptime_percentage", 100.0),
            total_trades=metrics.get("total_trades", 0),
            successful_trades=metrics.get("successful_trades", 0),
            failed_trades=metrics.get("failed_trades", 0),
            avg_slippage_pips=metrics.get("avg_slippage_pips", 0.0),
            connection_stability=metrics.get("connection_stability", 100.0)
        )
    
    async def add_websocket_connection(self, websocket: WebSocket):
        """Add a WebSocket connection for real-time updates"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send current state
        await self._send_initial_data(websocket)
        
    async def remove_websocket_connection(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def _monitor_brokers(self):
        """Background task to monitor broker connections and update data"""
        while self._running:
            try:
                # Update account data for all connected brokers
                for account_id, adapter in self.broker_adapters.items():
                    try:
                        if account_id in self.broker_accounts:
                            account = self.broker_accounts[account_id]
                            
                            # Check connection health
                            is_healthy = await self.health_monitor.check_broker_health(account_id)
                            
                            if is_healthy:
                                # Update account data
                                account_summary = await adapter.get_account_summary()
                                
                                account.balance = account_summary.balance
                                account.equity = account_summary.equity
                                account.unrealized_pl = account_summary.unrealized_pl
                                account.realized_pl = account_summary.realized_pl
                                account.margin_used = account_summary.margin_used
                                account.margin_available = account_summary.margin_available
                                account.connection_status = ConnectionStatus.CONNECTED
                                account.last_update = datetime.utcnow()
                                
                                # Broadcast update
                                await self._broadcast_broker_update(account_id, account)
                            else:
                                # Mark as disconnected
                                account.connection_status = ConnectionStatus.DISCONNECTED
                                await self._broadcast_broker_update(account_id, account)
                                
                    except Exception as e:
                        logger.error(f"Error updating broker {account_id}: {e}")
                        if account_id in self.broker_accounts:
                            self.broker_accounts[account_id].connection_status = ConnectionStatus.ERROR
                
                # Send aggregate update
                aggregate_data = await self.get_aggregate_data()
                await self._broadcast_aggregate_update(aggregate_data)
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in broker monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_broker_update(self, account_id: str, account: BrokerAccount):
        """Broadcast broker account update to all connected clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "BROKER_UPDATE",
            "account_id": account_id,
            "data": self._serialize_account(account)
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_aggregate_update(self, aggregate_data: AggregateData):
        """Broadcast aggregate data update to all connected clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "AGGREGATE_UPDATE",
            "data": self._serialize_aggregate_data(aggregate_data)
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_account_removed(self, account_id: str):
        """Broadcast account removal to all connected clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "ACCOUNT_REMOVED",
            "account_id": account_id
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.active_connections.remove(ws)
    
    async def _send_initial_data(self, websocket: WebSocket):
        """Send initial data to a newly connected client"""
        try:
            # Send all broker accounts
            for account_id, account in self.broker_accounts.items():
                message = {
                    "type": "BROKER_UPDATE",
                    "account_id": account_id,
                    "data": self._serialize_account(account)
                }
                await websocket.send_text(json.dumps(message, default=str))
            
            # Send aggregate data
            aggregate_data = await self.get_aggregate_data()
            message = {
                "type": "AGGREGATE_UPDATE",
                "data": self._serialize_aggregate_data(aggregate_data)
            }
            await websocket.send_text(json.dumps(message, default=str))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    def _serialize_account(self, account: BrokerAccount) -> Dict[str, Any]:
        """Serialize broker account for JSON transmission"""
        data = asdict(account)
        data["connection_status"] = account.connection_status.value
        return data
    
    def _serialize_aggregate_data(self, aggregate: AggregateData) -> Dict[str, Any]:
        """Serialize aggregate data for JSON transmission"""
        return asdict(aggregate)
    
    async def _load_broker_configurations(self):
        """Load existing broker configurations from storage"""
        # This would load from a database or configuration file
        # For now, we'll just log that it's not implemented
        logger.info("Broker configuration loading not implemented yet")

# Global dashboard manager instance
dashboard_manager = BrokerDashboardManager()

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await dashboard_manager.initialize()
    yield
    # Shutdown
    await dashboard_manager.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Broker Integration Dashboard API",
    description="Unified API for managing multiple broker accounts",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/api/brokers", response_model=List[Dict[str, Any]])
async def get_broker_accounts():
    """Get all broker accounts"""
    accounts = await dashboard_manager.get_broker_accounts()
    return [dashboard_manager._serialize_account(account) for account in accounts]

@app.get("/api/aggregate", response_model=Dict[str, Any])
async def get_aggregate_data():
    """Get aggregate data across all broker accounts"""
    aggregate = await dashboard_manager.get_aggregate_data()
    return dashboard_manager._serialize_aggregate_data(aggregate)

@app.post("/api/brokers")
async def add_broker_account(broker_config: Dict[str, Any]):
    """Add a new broker account"""
    account_id = await dashboard_manager.add_broker_account(broker_config)
    return {"account_id": account_id, "status": "added"}

@app.delete("/api/brokers/{account_id}")
async def remove_broker_account(account_id: str):
    """Remove a broker account"""
    success = await dashboard_manager.remove_broker_account(account_id)
    return {"account_id": account_id, "status": "removed" if success else "failed"}

@app.post("/api/brokers/{account_id}/reconnect")
async def reconnect_broker(account_id: str):
    """Reconnect a broker account"""
    success = await dashboard_manager.reconnect_broker(account_id)
    return {"account_id": account_id, "status": "reconnected" if success else "failed"}

@app.get("/api/brokers/{account_id}/performance", response_model=Dict[str, Any])
async def get_broker_performance(account_id: str):
    """Get performance metrics for a specific broker"""
    metrics = await dashboard_manager.get_broker_performance(account_id)
    return asdict(metrics)

@app.get("/api/brokers/{account_id}/capabilities")
async def get_broker_capabilities(account_id: str):
    """Get capabilities for a specific broker"""
    if account_id not in dashboard_manager.broker_accounts:
        raise HTTPException(status_code=404, detail="Broker account not found")
    
    account = dashboard_manager.broker_accounts[account_id]
    return {"capabilities": account.capabilities}

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await dashboard_manager.add_websocket_connection(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await dashboard_manager.remove_websocket_connection(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await dashboard_manager.remove_websocket_connection(websocket)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connected_brokers": len([acc for acc in dashboard_manager.broker_accounts.values() 
                                if acc.connection_status == ConnectionStatus.CONNECTED])
    }

if __name__ == "__main__":
    uvicorn.run(
        "broker_dashboard_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )