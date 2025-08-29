"""
Agent Manager for Trading System Orchestrator

Handles agent discovery, registration, health monitoring, and communication.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel

from .models import AgentStatus, AgentInfo, TradeSignal, TradeResult
from .exceptions import AgentException, TimeoutException
from .config import get_settings

logger = logging.getLogger(__name__)


class AgentHealthStatus(BaseModel):
    """Agent health status information"""
    agent_id: str
    status: str
    last_seen: datetime
    response_time_ms: float
    error_count: int
    success_rate: float


class AgentManager:
    """Manages communication and monitoring of trading agents"""
    
    def __init__(self):
        self.settings = get_settings()
        self.agents: Dict[str, AgentInfo] = {}
        self.health_status: Dict[str, AgentHealthStatus] = {}
        self.client = httpx.AsyncClient(timeout=self.settings.agent_request_timeout)
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
    async def start(self):
        """Start the agent manager"""
        logger.info("Starting Agent Manager")
        
        # Discover available agents
        await self.discover_agents()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Agent Manager started with {len(self.agents)} agents")
    
    async def stop(self):
        """Stop the agent manager"""
        logger.info("Stopping Agent Manager")
        self._shutdown = True
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        await self.client.aclose()
        logger.info("Agent Manager stopped")
    
    async def discover_agents(self):
        """Discover available trading agents"""
        logger.info("Discovering trading agents...")
        
        agent_types = [
            "market-analysis",
            "strategy-analysis", 
            "parameter-optimization",
            "learning-safety",
            "disagreement-engine",
            "data-collection",
            "continuous-improvement",
            "pattern-detection"
        ]
        
        for agent_type in agent_types:
            endpoint = self.settings.get_agent_endpoint(agent_type)
            if endpoint:
                try:
                    await self._register_agent(agent_type, endpoint)
                except Exception as e:
                    logger.warning(f"Failed to register agent {agent_type}: {e}")
    
    async def _register_agent(self, agent_type: str, endpoint: str):
        """Register a single agent"""
        try:
            # Try to contact the agent
            response = await self.client.get(f"{endpoint}/health")
            if response.status_code == 200:
                agent_info = AgentInfo(
                    agent_id=agent_type,
                    agent_type=agent_type,
                    endpoint=endpoint,
                    status=AgentStatus.ACTIVE,
                    last_seen=datetime.utcnow(),
                    capabilities=response.json().get("capabilities", [])
                )
                
                self.agents[agent_type] = agent_info
                self.health_status[agent_type] = AgentHealthStatus(
                    agent_id=agent_type,
                    status="healthy",
                    last_seen=datetime.utcnow(),
                    response_time_ms=response.elapsed.total_seconds() * 1000,
                    error_count=0,
                    success_rate=1.0
                )
                
                logger.info(f"Registered agent: {agent_type} at {endpoint}")
            else:
                logger.warning(f"Agent {agent_type} health check failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to register agent {agent_type}: {e}")
    
    async def list_agents(self) -> List:
        """List all registered agents with their information"""
        from .models import AgentInfo
        agent_list = []
        for agent_id, agent in self.agents.items():
            health = self.health_status.get(agent_id)
            agent_info = {
                "id": agent_id,
                "name": f"{agent_id.replace('-', ' ').title()} Agent",
                "type": agent_id.replace('-', '_'),
                "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status),
                "health": health.status if health else "unknown",
                "last_seen": health.last_seen.isoformat() if health and health.last_seen else None,
                "response_time_ms": health.response_time_ms if health else 0,
                "error_count": health.error_count if health else 0,
                "success_rate": health.success_rate if health else 0.0
            }
            agent_list.append(agent_info)
        return agent_list
    
    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get current status of an agent"""
        agent = self.agents.get(agent_id)
        return agent.status if agent else None
    
    async def get_all_agent_statuses(self) -> List:
        """Get status of all registered agents"""
        statuses = []
        for agent_id, agent in self.agents.items():
            health = self.health_status.get(agent_id)
            status = {
                "agent_id": agent_id,
                "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status),
                "health": health.status if health else "unknown",
                "last_seen": health.last_seen.isoformat() if health and health.last_seen else None,
                "response_time_ms": health.response_time_ms if health else 0,
                "error_count": health.error_count if health else 0,
                "success_rate": health.success_rate if health else 0.0
            }
            statuses.append(status)
        return statuses
    
    async def get_healthy_agents(self) -> List[str]:
        """Get list of healthy agent IDs"""
        healthy_agents = []
        for agent_id, health in self.health_status.items():
            if health.status == "healthy":
                healthy_agents.append(agent_id)
        return healthy_agents
    
    async def send_signal_to_agent(self, agent_id: str, signal: TradeSignal) -> Optional[TradeResult]:
        """Send a trading signal to a specific agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise AgentException(agent_id, "Agent not found")
        
        if agent.status != AgentStatus.ACTIVE:
            raise AgentException(agent_id, f"Agent is not active (status: {agent.status})")
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.post(
                f"{agent.endpoint}/process_signal",
                json=signal.dict(),
                timeout=self.settings.agent_request_timeout
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                # Update health status
                await self._update_agent_health(agent_id, True, response_time)
                
                result_data = response.json()
                return TradeResult(**result_data)
            else:
                await self._update_agent_health(agent_id, False, response_time)
                raise AgentException(agent_id, f"Signal processing failed: {response.status_code}")
                
        except httpx.TimeoutException:
            await self._update_agent_health(agent_id, False, None)
            raise TimeoutException(f"signal_to_{agent_id}", self.settings.agent_request_timeout)
        except Exception as e:
            await self._update_agent_health(agent_id, False, None)
            raise AgentException(agent_id, f"Communication error: {e}")
    
    async def broadcast_signal(self, signal: TradeSignal, target_agents: Optional[List[str]] = None) -> Dict[str, TradeResult]:
        """Broadcast a signal to multiple agents"""
        if target_agents is None:
            target_agents = await self.get_healthy_agents()
        
        results = {}
        tasks = []
        
        for agent_id in target_agents:
            task = asyncio.create_task(
                self._safe_send_signal(agent_id, signal)
            )
            tasks.append((agent_id, task))
        
        # Wait for all responses
        for agent_id, task in tasks:
            try:
                result = await task
                if result:
                    results[agent_id] = result
            except Exception as e:
                logger.error(f"Error getting result from agent {agent_id}: {e}")
        
        return results
    
    async def _safe_send_signal(self, agent_id: str, signal: TradeSignal) -> Optional[TradeResult]:
        """Safely send signal to agent with error handling"""
        try:
            return await self.send_signal_to_agent(agent_id, signal)
        except Exception as e:
            logger.error(f"Failed to send signal to agent {agent_id}: {e}")
            return None
    
    async def _health_check_loop(self):
        """Continuously monitor agent health"""
        while not self._shutdown:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.settings.agent_health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered agents"""
        if not self.agents:
            return
        
        tasks = []
        for agent_id, agent in self.agents.items():
            task = asyncio.create_task(
                self._check_agent_health(agent_id, agent)
            )
            tasks.append(task)
        
        # Wait for all health checks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_agent_health(self, agent_id: str, agent: AgentInfo):
        """Check health of a single agent"""
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.get(
                f"{agent.endpoint}/health",
                timeout=5.0  # Shorter timeout for health checks
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                # Agent is healthy
                agent.status = AgentStatus.ACTIVE
                agent.last_seen = datetime.utcnow()
                await self._update_agent_health(agent_id, True, response_time)
            else:
                # Agent responded but with error
                await self._update_agent_health(agent_id, False, response_time)
                await self._handle_unhealthy_agent(agent_id, f"HTTP {response.status_code}")
                
        except httpx.TimeoutException:
            await self._update_agent_health(agent_id, False, None)
            await self._handle_unhealthy_agent(agent_id, "Timeout")
        except Exception as e:
            await self._update_agent_health(agent_id, False, None)
            await self._handle_unhealthy_agent(agent_id, str(e))
    
    async def _update_agent_health(self, agent_id: str, success: bool, response_time: Optional[float]):
        """Update agent health statistics"""
        if agent_id not in self.health_status:
            return
        
        health = self.health_status[agent_id]
        
        if success:
            health.status = "healthy"
            health.last_seen = datetime.utcnow()
            if response_time:
                health.response_time_ms = response_time
            # Reset error count on success
            health.error_count = max(0, health.error_count - 1)
        else:
            health.error_count += 1
            if health.error_count >= 3:
                health.status = "unhealthy"
        
        # Calculate success rate (simple moving average)
        health.success_rate = max(0.0, 1.0 - (health.error_count / 10.0))
    
    async def _handle_unhealthy_agent(self, agent_id: str, error: str):
        """Handle an unhealthy agent"""
        agent = self.agents.get(agent_id)
        if agent:
            agent.status = AgentStatus.ERROR
            logger.warning(f"Agent {agent_id} is unhealthy: {error}")
            
            # TODO: Implement recovery strategies
            # - Restart agent
            # - Remove from active pool temporarily
            # - Send alerts
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, AgentInfo]:
        """Get information about all agents"""
        return self.agents.copy()
    
    def get_health_summary(self) -> Dict[str, AgentHealthStatus]:
        """Get health summary for all agents"""
        return self.health_status.copy()
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Attempt to restart an agent"""
        # TODO: Implement agent restart logic
        # This would depend on how agents are deployed (Docker, systemd, etc.)
        logger.info(f"Restart requested for agent {agent_id}")
        return False
    
    async def remove_agent(self, agent_id: str):
        """Remove an agent from management"""
        if agent_id in self.agents:
            del self.agents[agent_id]
        if agent_id in self.health_status:
            del self.health_status[agent_id]
        logger.info(f"Removed agent {agent_id}")
    
    async def health_check_all(self):
        """Perform health check on all agents"""
        await self._perform_health_checks()
    
    async def call_agent(self, agent_id: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific method on an agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise AgentException(agent_id, "Agent not found")
        
        if agent.status != AgentStatus.ACTIVE:
            raise AgentException(agent_id, f"Agent is not active (status: {agent.status})")
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.post(
                f"{agent.endpoint}/{method}",
                json=data,
                timeout=self.settings.agent_request_timeout
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                # Update health status
                await self._update_agent_health(agent_id, True, response_time)
                
                result_data = response.json()
                return result_data
            else:
                await self._update_agent_health(agent_id, False, response_time)
                raise AgentException(agent_id, f"Method call failed: {response.status_code}")
                
        except httpx.TimeoutException:
            await self._update_agent_health(agent_id, False, None)
            raise TimeoutException(f"call_{agent_id}_{method}", self.settings.agent_request_timeout)
        except Exception as e:
            await self._update_agent_health(agent_id, False, None)
            raise AgentException(agent_id, f"Communication error: {e}")