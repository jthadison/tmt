"""
Execution Engine Integration Client for Risk Analytics.

Provides seamless integration with the execution engine for real-time
position updates, order monitoring, and risk data synchronization.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from uuid import UUID

import structlog

from ..core.models import Position, AssetClass


logger = structlog.get_logger(__name__)


class ExecutionEngineClient:
    """
    Client for integrating with the TMT Execution Engine MVP.
    Provides real-time position updates and order monitoring.
    """
    
    def __init__(
        self,
        execution_engine_url: str = "http://localhost:8004",
        timeout: float = 5.0
    ):
        self.execution_engine_url = execution_engine_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
        # Connection management
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        # Event callbacks
        self.position_update_callbacks: List[Callable] = []
        self.order_update_callbacks: List[Callable] = []
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.avg_response_time = 0.0
        
        # Position cache
        self.cached_positions: Dict[str, List[Position]] = {}
        self.last_position_update: Dict[str, datetime] = {}
    
    async def connect(self) -> bool:
        """Establish connection to execution engine."""
        try:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            # Test connection
            health_status = await self.get_health_status()
            if health_status and health_status.get('status') == 'healthy':
                self.is_connected = True
                logger.info("Connected to execution engine", url=self.execution_engine_url)
                return True
            else:
                logger.error("Execution engine health check failed")
                return False
                
        except Exception as e:
            logger.error("Failed to connect to execution engine", error=str(e))
            return False
    
    async def disconnect(self):
        """Close connection to execution engine."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        logger.info("Disconnected from execution engine")
    
    async def get_health_status(self) -> Optional[Dict]:
        """Get execution engine health status."""
        try:
            start_time = time.perf_counter()
            
            async with self.session.get(f"{self.execution_engine_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return data
                else:
                    logger.warning("Health check failed", status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Health check error", error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get current positions for an account."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.execution_engine_url}/api/v1/positions"
            params = {"account_id": account_id}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    positions_data = await response.json()
                    
                    # Convert to Position objects
                    positions = []
                    for pos_data in positions_data:
                        position = self._convert_to_position(pos_data)
                        if position:
                            positions.append(position)
                    
                    # Cache positions
                    self.cached_positions[account_id] = positions
                    self.last_position_update[account_id] = datetime.now()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    # Notify callbacks
                    await self._notify_position_callbacks(account_id, positions)
                    
                    return positions
                    
                else:
                    logger.warning("Failed to get positions", 
                                 account_id=account_id, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return []
                    
        except Exception as e:
            logger.error("Error getting positions", 
                        account_id=account_id, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return []
    
    async def get_position_by_id(self, position_id: UUID) -> Optional[Position]:
        """Get specific position by ID."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.execution_engine_url}/api/v1/positions/{position_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    pos_data = await response.json()
                    position = self._convert_to_position(pos_data)
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return position
                    
                elif response.status == 404:
                    logger.debug("Position not found", position_id=position_id)
                    return None
                    
                else:
                    logger.warning("Failed to get position", 
                                 position_id=position_id, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error getting position", 
                        position_id=position_id, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_account_summary(self, account_id: str) -> Optional[Dict]:
        """Get account summary information."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.execution_engine_url}/api/v1/accounts/{account_id}/summary"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    summary_data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return summary_data
                    
                else:
                    logger.warning("Failed to get account summary", 
                                 account_id=account_id, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error getting account summary", 
                        account_id=account_id, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_performance_metrics(self) -> Optional[Dict]:
        """Get execution engine performance metrics."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.execution_engine_url}/api/v1/performance/metrics"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    metrics_data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return metrics_data
                    
                else:
                    logger.warning("Failed to get performance metrics", 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error getting performance metrics", error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def trigger_kill_switch(self, account_id: str, reason: str) -> bool:
        """Trigger kill switch for emergency position closing."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.execution_engine_url}/api/v1/risk/{account_id}/kill-switch"
            params = {"reason": reason}
            
            async with self.session.post(url, params=params) as response:
                success = response.status in [200, 201]
                
                # Track performance
                response_time = (time.perf_counter() - start_time) * 1000
                self._update_performance_metrics(response_time, success=success)
                
                if success:
                    logger.critical("Kill switch activated", 
                                  account_id=account_id, 
                                  reason=reason)
                else:
                    logger.error("Failed to activate kill switch", 
                               account_id=account_id, 
                               status=response.status)
                
                return success
                
        except Exception as e:
            logger.error("Error activating kill switch", 
                        account_id=account_id, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return False
    
    def _convert_to_position(self, pos_data: Dict) -> Optional[Position]:
        """Convert API position data to Position object."""
        try:
            # Map asset class
            instrument = pos_data.get('instrument', '')
            if '_' in instrument and 'USD' in instrument:
                asset_class = AssetClass.FOREX
            else:
                asset_class = AssetClass.FOREX  # Default to forex for now
            
            position = Position(
                position_id=UUID(pos_data['position_id']) if 'position_id' in pos_data else UUID(pos_data.get('id', pos_data.get('positionId'))),
                account_id=pos_data['account_id'],
                instrument=instrument,
                asset_class=asset_class,
                units=Decimal(str(pos_data.get('units', 0))),
                average_price=Decimal(str(pos_data.get('average_price', pos_data.get('averagePrice', 0)))),
                current_price=Decimal(str(pos_data.get('current_price', pos_data.get('currentPrice', 0)))),
                market_value=Decimal(str(pos_data.get('market_value', pos_data.get('marketValue', 0)))),
                unrealized_pl=Decimal(str(pos_data.get('unrealized_pl', pos_data.get('unrealizedPL', 0)))),
                realized_pl=Decimal(str(pos_data.get('realized_pl', pos_data.get('realizedPL', 0)))),
                daily_pl=Decimal(str(pos_data.get('daily_pl', pos_data.get('dailyPL', 0)))),
                opened_at=datetime.fromisoformat(pos_data.get('opened_at', pos_data.get('openTime', datetime.now().isoformat())).replace('Z', '+00:00'))
            )
            
            return position
            
        except Exception as e:
            logger.error("Error converting position data", 
                        pos_data=pos_data, 
                        error=str(e))
            return None
    
    def _update_performance_metrics(self, response_time: float, success: bool):
        """Update client performance metrics."""
        self.request_count += 1
        
        if not success:
            self.error_count += 1
        
        if response_time > 0:
            # Calculate running average
            if self.avg_response_time == 0:
                self.avg_response_time = response_time
            else:
                self.avg_response_time = (self.avg_response_time * 0.9 + response_time * 0.1)
    
    async def _notify_position_callbacks(self, account_id: str, positions: List[Position]):
        """Notify registered callbacks of position updates."""
        for callback in self.position_update_callbacks:
            try:
                await callback(account_id, positions)
            except Exception as e:
                logger.error("Error in position update callback", error=str(e))
    
    def register_position_callback(self, callback: Callable):
        """Register callback for position updates."""
        self.position_update_callbacks.append(callback)
        logger.debug("Registered position update callback")
    
    def register_order_callback(self, callback: Callable):
        """Register callback for order updates."""
        self.order_update_callbacks.append(callback)
        logger.debug("Registered order update callback")
    
    async def start_position_monitoring(self, account_ids: List[str], interval_seconds: float = 1.0):
        """Start continuous position monitoring for specified accounts."""
        logger.info("Starting position monitoring", 
                   accounts=account_ids, 
                   interval=interval_seconds)
        
        async def monitor_positions():
            while self.is_connected:
                try:
                    for account_id in account_ids:
                        await self.get_positions(account_id)
                    
                    await asyncio.sleep(interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in position monitoring", error=str(e))
                    await asyncio.sleep(interval_seconds)
        
        # Start monitoring task
        asyncio.create_task(monitor_positions())
    
    def get_cached_positions(self, account_id: str) -> List[Position]:
        """Get cached positions for an account."""
        return self.cached_positions.get(account_id, [])
    
    def get_client_performance(self) -> Dict:
        """Get client performance metrics."""
        success_rate = (self.request_count - self.error_count) / self.request_count if self.request_count > 0 else 1.0
        
        return {
            "is_connected": self.is_connected,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "success_rate": success_rate,
            "avg_response_time_ms": self.avg_response_time,
            "cached_accounts": len(self.cached_positions),
            "last_update_times": {
                account_id: update_time.isoformat() 
                for account_id, update_time in self.last_position_update.items()
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()