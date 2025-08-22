"""
Trading System Orchestrator - Core Implementation

Manages the lifecycle and coordination of 8 specialized AI trading agents.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import json

from fastapi import WebSocket

from .models import (
    SystemStatus, AgentStatus, AccountStatus, TradeSignal, 
    SystemMetrics, AgentInfo, AccountInfo, TradeResult
)
from .config import get_settings
from .agent_manager import AgentManager
from .event_bus import EventBus
from .circuit_breaker import CircuitBreakerManager
from .oanda_client import OandaClient
from .safety_monitor import SafetyMonitor
from .exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Central orchestrator that coordinates all trading agents and manages
    the overall trading system lifecycle.
    """
    
    def __init__(self):
        """Initialize the orchestrator with configuration"""
        self.settings = get_settings()
        self.running = False
        self.trading_enabled = False
        self.start_time = None
        
        # Core components
        self.event_bus = EventBus()
        self.oanda_client = OandaClient()
        self.agent_manager = AgentManager()
        self.circuit_breaker = CircuitBreakerManager(self.event_bus)
        self.safety_monitor = SafetyMonitor(self.event_bus, self.oanda_client)
        
        # Execution engine integration
        self.execution_engine_url = "http://localhost:8004"
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # System state
        self.system_events: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "signals_processed": 0,
            "trades_executed": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "average_latency": 0.0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start the orchestrator and all subsystems"""
        try:
            logger.info("Starting Trading System Orchestrator...")
            self.start_time = datetime.now(timezone.utc)
            
            # Start core components
            await self.event_bus.start()
            await self.agent_manager.start()
            await self.safety_monitor.start()
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._event_processing_loop()),
                asyncio.create_task(self._metrics_collection_loop()),
                asyncio.create_task(self._websocket_broadcast_loop())
            ]
            
            self.running = True
            await self._emit_event("system.started", {"timestamp": self.start_time.isoformat()})
            
            logger.info("Trading System Orchestrator started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start orchestrator: {e}")
            await self.stop()
            raise OrchestratorException(f"Startup failed: {e}", status_code=500)
    
    async def stop(self):
        """Stop the orchestrator and all subsystems gracefully"""
        try:
            logger.info("Stopping Trading System Orchestrator...")
            
            # Stop trading first
            if self.trading_enabled:
                await self.stop_trading()
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Stop components
            await self.safety_monitor.stop()
            await self.agent_manager.stop()
            await self.oanda_client.close()
            await self.event_bus.stop()
            
            self.running = False
            await self._emit_event("system.stopped", {"timestamp": datetime.now(timezone.utc).isoformat()})
            
            logger.info("Trading System Orchestrator stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def start_trading(self):
        """Start automated trading"""
        if not self.running:
            raise OrchestratorException("Orchestrator not running", status_code=503)
        
        if self.trading_enabled:
            raise OrchestratorException("Trading already enabled", status_code=400)
        
        try:
            # Perform safety checks
            await self.safety_monitor.pre_trading_checks()
            
            # Check circuit breakers
            if not self.circuit_breaker.can_trade():
                raise OrchestratorException("Circuit breakers prevent trading", status_code=423)
            
            # Verify OANDA connection
            await self.oanda_client.verify_connection()
            
            # Enable trading
            self.trading_enabled = True
            await self._emit_event("trading.started", {"timestamp": datetime.now(timezone.utc).isoformat()})
            
            logger.info("Automated trading started")
            
        except Exception as e:
            logger.error(f"Failed to start trading: {e}")
            raise OrchestratorException(f"Failed to start trading: {e}", status_code=500)
    
    async def stop_trading(self):
        """Stop automated trading gracefully"""
        if not self.trading_enabled:
            return
        
        try:
            self.trading_enabled = False
            
            # Notify all agents to stop trading
            from .event_bus import Event
            import uuid
            stop_event = Event(
                event_id=str(uuid.uuid4()),
                event_type="trading.stop_requested",
                timestamp=datetime.now(timezone.utc),
                source="orchestrator",
                data={}
            )
            await self.event_bus.publish(stop_event)
            
            # Wait for current operations to complete
            await asyncio.sleep(1)
            
            await self._emit_event("trading.stopped", {"timestamp": datetime.now(timezone.utc).isoformat()})
            
            logger.info("Automated trading stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading: {e}")
            raise OrchestratorException(f"Failed to stop trading: {e}", status_code=500)
    
    async def emergency_stop(self, reason: str):
        """Emergency stop - immediately halt all trading"""
        try:
            logger.warning(f"Emergency stop triggered: {reason}")
            
            # Immediate stop
            self.trading_enabled = False
            
            # Trigger circuit breakers
            await self.circuit_breaker.trigger_emergency_stop(reason)
            
            # Notify all agents immediately
            from .event_bus import Event
            import uuid
            emergency_event = Event(
                event_id=str(uuid.uuid4()),
                event_type="emergency.stop",
                timestamp=datetime.now(timezone.utc),
                source="orchestrator",
                data={"reason": reason}
            )
            await self.event_bus.publish(emergency_event)
            
            # Close all positions if configured to do so
            if self.settings.emergency_close_positions:
                await self.oanda_client.close_all_positions()
            
            await self._emit_event("emergency.stop", {
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.warning("Emergency stop completed")
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
            raise OrchestratorException(f"Emergency stop failed: {e}", status_code=500)
    
    async def process_signal(self, signal: TradeSignal) -> TradeResult:
        """Process a trading signal through the agent pipeline"""
        if not self.trading_enabled:
            raise OrchestratorException("Trading not enabled", status_code=423)
        
        signal_start_time = time.time()
        
        try:
            # Emit signal received event
            await self._emit_event("signal.received", {
                "signal_id": signal.id,
                "instrument": signal.instrument,
                "direction": signal.direction,
                "confidence": signal.confidence
            })
            
            # Safety checks
            if not await self.safety_monitor.validate_signal(signal):
                return TradeResult(
                    success=False,
                    signal_id=signal.id,
                    message="Failed safety validation"
                )
            
            # Circuit breaker check
            if not self.circuit_breaker.can_trade():
                return TradeResult(
                    success=False,
                    signal_id=signal.id,
                    message="Circuit breaker active"
                )
            
            # Process through disagreement engine - convert to expected format
            signal_data = signal.dict()
            if "timestamp" in signal_data and hasattr(signal_data["timestamp"], "isoformat"):
                signal_data["timestamp"] = signal_data["timestamp"].isoformat()
            
            # Map fields to disagreement engine format
            disagreement_signal = {
                "symbol": signal.instrument,
                "direction": signal.direction,
                "strength": signal.confidence,
                "price": signal.entry_price or 1.0,  # Use entry_price or default
                "stop_loss": signal.stop_loss or 0.0,
                "take_profit": signal.take_profit or 0.0
            }
            
            disagreement_result = await self.agent_manager.call_agent(
                "disagreement-engine",
                "signals/process",
                {
                    "signal_id": signal.id,
                    "signal": disagreement_signal,
                    "accounts": []  # TODO: Get actual accounts from OANDA client
                }
            )
            
            if not disagreement_result.get("approved", False):
                return TradeResult(
                    success=False,
                    signal_id=signal.id,
                    message="Disagreement engine rejection"
                )
            
            # Get optimized parameters
            param_result = await self.agent_manager.call_agent(
                "parameter-optimization",
                "optimize",
                {"signal": signal_data}
            )
            
            # Execute trade via execution engine (fallback to OANDA client if unavailable)
            trade_result = await self._execute_via_execution_engine(signal, param_result.get("parameters", {}))
            
            if not trade_result.success:
                # Fallback to direct OANDA client
                logger.info("Execution engine unavailable, falling back to direct OANDA execution")
                trade_result = await self.oanda_client.execute_trade(
                    signal,
                    param_result.get("parameters", {})
                )
            
            # Record metrics
            processing_time = time.time() - signal_start_time
            self.performance_metrics["signals_processed"] += 1
            self.performance_metrics["average_latency"] = (
                self.performance_metrics["average_latency"] * 0.9 + processing_time * 0.1
            )
            
            if trade_result.status == "executed":
                self.performance_metrics["trades_executed"] += 1
            
            # Emit completion event
            await self._emit_event("signal.processed", {
                "signal_id": signal.id,
                "result": trade_result.dict(),
                "processing_time": processing_time
            })
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.id}: {e}")
            await self._emit_event("signal.error", {
                "signal_id": signal.id,
                "error": str(e)
            })
            return TradeResult(
                success=False,
                signal_id=signal.id,
                message=str(e)
            )
    
    async def _execute_via_execution_engine(self, signal: TradeSignal, parameters: Dict) -> TradeResult:
        """Execute trade via execution engine service"""
        try:
            import aiohttp
            
            # Convert signal to execution engine order format
            order_request = {
                "account_id": "default",  # Would be configured per account in production
                "instrument": signal.instrument,
                "order_type": "market",
                "side": "buy" if signal.direction == "long" else "sell",
                "units": parameters.get("position_size", 10000),
                "take_profit_price": signal.take_profit,
                "stop_loss_price": signal.stop_loss,
                "client_extensions": {
                    "id": signal.id,
                    "tag": "orchestrator",
                    "comment": f"Signal {signal.id} - confidence {signal.confidence}"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.execution_engine_url}/api/orders",
                    json=order_request,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return TradeResult(
                            success=True,
                            signal_id=signal.id,
                            order_id=result.get("order_id"),
                            status="executed",
                            message="Order submitted to execution engine",
                            execution_price=result.get("execution_price"),
                            timestamp=datetime.now(timezone.utc)
                        )
                    else:
                        error_text = await response.text()
                        logger.warning(f"Execution engine returned {response.status}: {error_text}")
                        return TradeResult(
                            success=False,
                            signal_id=signal.id,
                            message=f"Execution engine error: {response.status}"
                        )
                        
        except Exception as e:
            logger.debug(f"Execution engine unavailable: {e}")
            return TradeResult(
                success=False,
                signal_id=signal.id,
                message=f"Execution engine connection failed: {e}"
            )
    
    async def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        agent_statuses = await self.agent_manager.get_all_agent_statuses()
        
        oanda_status = await self.oanda_client.get_connection_status()
        
        # Count healthy agents - agent_statuses is a list of dicts
        healthy_agents = len([s for s in agent_statuses if s.get("health") == "healthy"])
        
        return SystemStatus(
            running=self.running,
            trading_enabled=self.trading_enabled,
            uptime_seconds=int((datetime.now(timezone.utc) - self.start_time).total_seconds()) if self.start_time else 0,
            connected_agents=healthy_agents,
            total_agents=len(agent_statuses),
            circuit_breaker_status=await self.circuit_breaker.get_status(),
            oanda_connection=oanda_status.get("connected", False),
            last_update=datetime.now(timezone.utc)
        )
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get system performance metrics"""
        return SystemMetrics(
            signals_processed=self.performance_metrics["signals_processed"],
            trades_executed=self.performance_metrics["trades_executed"],
            total_pnl=self.performance_metrics["total_pnl"],
            win_rate=self.performance_metrics["win_rate"],
            average_latency=self.performance_metrics["average_latency"],
            uptime_seconds=int((datetime.now(timezone.utc) - self.start_time).total_seconds()) if self.start_time else 0,
            memory_usage_mb=0,  # TODO: Implement actual memory monitoring
            cpu_usage_percent=0  # TODO: Implement actual CPU monitoring
        )
    
    async def list_agents(self) -> List[AgentInfo]:
        """List all registered agents"""
        return await self.agent_manager.list_agents()
    
    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get status of specific agent"""
        return await self.agent_manager.get_agent_status(agent_id)
    
    async def restart_agent(self, agent_id: str):
        """Restart specific agent"""
        await self.agent_manager.restart_agent(agent_id)
    
    async def list_accounts(self) -> List[AccountInfo]:
        """List all OANDA accounts"""
        return await self.oanda_client.list_accounts()
    
    async def get_account_status(self, account_id: str) -> AccountStatus:
        """Get status of specific account"""
        return await self.oanda_client.get_account_status(account_id)
    
    async def enable_account(self, account_id: str):
        """Enable trading on specific account"""
        await self.oanda_client.enable_account(account_id)
        await self._emit_event("account.enabled", {"account_id": account_id})
    
    async def disable_account(self, account_id: str):
        """Disable trading on specific account"""
        await self.oanda_client.disable_account(account_id)
        await self._emit_event("account.disabled", {"account_id": account_id})
    
    async def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent system events"""
        return self.system_events[-limit:] if self.system_events else []
    
    async def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        return self.trade_history[-limit:] if self.trade_history else []
    
    async def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions"""
        return await self.oanda_client.get_current_positions()
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections for real-time updates"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            while True:
                # Keep connection alive
                await asyncio.sleep(30)
                await websocket.ping()
        except Exception as e:
            logger.debug(f"WebSocket connection closed: {e}")
        finally:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit a system event"""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        self.system_events.append(event)
        
        # Keep only last 1000 events
        if len(self.system_events) > 1000:
            self.system_events = self.system_events[-1000:]
        
        # Publish to event bus
        from .event_bus import Event
        import uuid
        event_obj = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            source="orchestrator",
            data=data
        )
        await self.event_bus.publish(event_obj)
    
    async def _health_check_loop(self):
        """Background task for health monitoring"""
        while self.running:
            try:
                # Check agent health
                await self.agent_manager.health_check_all()
                
                # Check OANDA connection
                await self.oanda_client.health_check()
                
                # Check circuit breakers
                await self.circuit_breaker.health_check()
                
                await asyncio.sleep(self.settings.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _event_processing_loop(self):
        """Background task for processing events"""
        while self.running:
            try:
                # Process any pending events
                await self.event_bus.process_pending_events()
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                await asyncio.sleep(5)
    
    async def _metrics_collection_loop(self):
        """Background task for collecting performance metrics"""
        while self.running:
            try:
                # Update performance metrics
                await self._update_performance_metrics()
                await asyncio.sleep(60)  # Update metrics every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(10)
    
    async def _websocket_broadcast_loop(self):
        """Background task for broadcasting updates to WebSocket clients"""
        while self.running:
            try:
                if self.websocket_connections:
                    # Broadcast system status to all connected clients
                    status = await self.get_system_status()
                    message = {
                        "type": "system_status",
                        "data": status.dict()
                    }
                    
                    # Send to all connected clients
                    disconnected = []
                    for websocket in self.websocket_connections:
                        try:
                            await websocket.send_json(message)
                        except Exception:
                            disconnected.append(websocket)
                    
                    # Remove disconnected clients
                    for ws in disconnected:
                        self.websocket_connections.remove(ws)
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                await asyncio.sleep(10)
    
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            # Get current P&L from OANDA
            total_pnl = await self.oanda_client.get_total_pnl()
            self.performance_metrics["total_pnl"] = total_pnl
            
            # Calculate win rate from recent trades
            if self.trade_history:
                recent_trades = self.trade_history[-100:]  # Last 100 trades
                winning_trades = len([t for t in recent_trades if t.get("pnl", 0) > 0])
                self.performance_metrics["win_rate"] = winning_trades / len(recent_trades)
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")