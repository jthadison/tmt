"""
Tests for Agent Manager
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.agent_manager import AgentManager, AgentHealthStatus
from app.models import AgentStatus, AgentInfo, TradeSignal, TradeResult
from app.exceptions import AgentException, TimeoutException


class TestAgentManager:
    """Test AgentManager functionality"""
    
    @pytest.fixture
    async def agent_manager(self, test_settings, mock_httpx_client):
        """Create AgentManager instance for testing"""
        with patch('app.agent_manager.get_settings', return_value=test_settings):
            with patch('app.agent_manager.httpx.AsyncClient', return_value=mock_httpx_client):
                manager = AgentManager()
                yield manager
                await manager.stop()
    
    @pytest.mark.asyncio
    async def test_agent_manager_initialization(self, agent_manager):
        """Test AgentManager initialization"""
        assert agent_manager.agents == {}
        assert agent_manager.health_status == {}
        assert agent_manager._shutdown is False
    
    @pytest.mark.asyncio
    async def test_discover_agents_success(self, agent_manager, mock_httpx_client):
        """Test successful agent discovery"""
        # Mock successful health responses
        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {"capabilities": ["trading", "analysis"]}
        health_response.elapsed.total_seconds.return_value = 0.1
        mock_httpx_client.get.return_value = health_response
        
        await agent_manager.discover_agents()
        
        # Should discover all 8 agents
        expected_agents = [
            "market-analysis", "strategy-analysis", "parameter-optimization",
            "learning-safety", "disagreement-engine", "data-collection",
            "continuous-improvement", "pattern-detection"
        ]
        
        assert len(agent_manager.agents) == 8
        for agent_type in expected_agents:
            assert agent_type in agent_manager.agents
            assert agent_type in agent_manager.health_status
            
            agent = agent_manager.agents[agent_type]
            assert agent.agent_id == agent_type
            assert agent.status == AgentStatus.ACTIVE
            assert isinstance(agent.last_seen, datetime)
    
    @pytest.mark.asyncio
    async def test_discover_agents_partial_failure(self, agent_manager, mock_httpx_client):
        """Test agent discovery with some agents failing"""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # First 4 agents succeed, next 4 fail
            if call_count <= 4:
                response = Mock()
                response.status_code = 200
                response.json.return_value = {"capabilities": ["trading"]}
                response.elapsed.total_seconds.return_value = 0.1
                return response
            else:
                response = Mock()
                response.status_code = 500
                return response
        
        mock_httpx_client.get.side_effect = mock_get
        
        await agent_manager.discover_agents()
        
        # Should discover only 4 agents (the successful ones)
        assert len(agent_manager.agents) == 4
        assert len(agent_manager.health_status) == 4
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, agent_manager, mock_httpx_client):
        """Test starting and stopping agent manager"""
        # Mock successful discovery
        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {"capabilities": ["trading"]}
        health_response.elapsed.total_seconds.return_value = 0.1
        mock_httpx_client.get.return_value = health_response
        
        await agent_manager.start()
        
        # Should have discovered agents and started health check task
        assert len(agent_manager.agents) > 0
        assert agent_manager._health_check_task is not None
        
        await agent_manager.stop()
        
        # Should have stopped cleanly
        assert agent_manager._shutdown is True
    
    @pytest.mark.asyncio
    async def test_send_signal_to_agent_success(self, agent_manager, sample_trade_signal, mock_httpx_client):
        """Test successfully sending signal to agent"""
        # Register a test agent
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="test-agent",
            endpoint="http://localhost:8001",
            status=AgentStatus.ACTIVE,
            last_seen=datetime.utcnow(),
            capabilities=["signal_processing"]
        )
        agent_manager.agents["test-agent"] = agent_info
        agent_manager.health_status["test-agent"] = AgentHealthStatus(
            agent_id="test-agent",
            status="healthy",
            last_seen=datetime.utcnow(),
            response_time_ms=100.0,
            error_count=0,
            success_rate=1.0
        )
        
        # Mock successful signal processing response
        signal_response = Mock()
        signal_response.status_code = 200
        signal_response.json.return_value = {
            "success": True,
            "trade_id": "12345",
            "executed_price": 1.0500,
            "executed_units": 1000.0,
            "pnl": 0.0,
            "commission": 2.50,
            "financing": 0.25,
            "message": "Signal processed successfully"
        }
        mock_httpx_client.post.return_value = signal_response
        
        result = await agent_manager.send_signal_to_agent("test-agent", sample_trade_signal)
        
        assert isinstance(result, TradeResult)
        assert result.success is True
        assert result.trade_id == "12345"
        assert result.executed_price == 1.0500
        
        # Health status should be updated
        health = agent_manager.health_status["test-agent"]
        assert health.error_count == 0
        assert health.success_rate > 0.9
    
    @pytest.mark.asyncio
    async def test_send_signal_agent_not_found(self, agent_manager, sample_trade_signal):
        """Test sending signal to non-existent agent"""
        with pytest.raises(AgentException) as excinfo:
            await agent_manager.send_signal_to_agent("non-existent-agent", sample_trade_signal)
        
        assert "Agent not found" in str(excinfo.value)
        assert excinfo.value.agent_id == "non-existent-agent"
    
    @pytest.mark.asyncio
    async def test_send_signal_agent_inactive(self, agent_manager, sample_trade_signal):
        """Test sending signal to inactive agent"""
        # Register an inactive agent
        agent_info = AgentInfo(
            agent_id="inactive-agent",
            agent_type="inactive-agent", 
            endpoint="http://localhost:8001",
            status=AgentStatus.INACTIVE,
            last_seen=datetime.utcnow()
        )
        agent_manager.agents["inactive-agent"] = agent_info
        
        with pytest.raises(AgentException) as excinfo:
            await agent_manager.send_signal_to_agent("inactive-agent", sample_trade_signal)
        
        assert "Agent is not active" in str(excinfo.value)
        assert "INACTIVE" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_send_signal_timeout(self, agent_manager, sample_trade_signal, mock_httpx_client):
        """Test signal sending with timeout"""
        # Register a test agent
        agent_info = AgentInfo(
            agent_id="timeout-agent",
            agent_type="timeout-agent",
            endpoint="http://localhost:8001",
            status=AgentStatus.ACTIVE,
            last_seen=datetime.utcnow()
        )
        agent_manager.agents["timeout-agent"] = agent_info
        agent_manager.health_status["timeout-agent"] = AgentHealthStatus(
            agent_id="timeout-agent",
            status="healthy",
            last_seen=datetime.utcnow(),
            response_time_ms=100.0,
            error_count=0,
            success_rate=1.0
        )
        
        # Mock timeout
        import httpx
        mock_httpx_client.post.side_effect = httpx.TimeoutException("Request timed out")
        
        with pytest.raises(TimeoutException) as excinfo:
            await agent_manager.send_signal_to_agent("timeout-agent", sample_trade_signal)
        
        assert "signal_to_timeout-agent" in str(excinfo.value)
        
        # Health status should be updated with failure
        health = agent_manager.health_status["timeout-agent"]
        assert health.error_count > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_signal_success(self, agent_manager, sample_trade_signal, mock_httpx_client):
        """Test broadcasting signal to multiple agents"""
        # Register multiple test agents
        agents = ["agent-1", "agent-2", "agent-3"]
        for agent_id in agents:
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_id,
                endpoint=f"http://localhost:800{agent_id[-1]}",
                status=AgentStatus.ACTIVE,
                last_seen=datetime.utcnow()
            )
            agent_manager.agents[agent_id] = agent_info
            agent_manager.health_status[agent_id] = AgentHealthStatus(
                agent_id=agent_id,
                status="healthy",
                last_seen=datetime.utcnow(),
                response_time_ms=100.0,
                error_count=0,
                success_rate=1.0
            )
        
        # Mock successful responses
        signal_response = Mock()
        signal_response.status_code = 200
        signal_response.json.return_value = {
            "success": True,
            "message": "Processed successfully"
        }
        mock_httpx_client.post.return_value = signal_response
        
        results = await agent_manager.broadcast_signal(sample_trade_signal, agents)
        
        assert len(results) == 3
        for agent_id in agents:
            assert agent_id in results
            assert results[agent_id].success is True
    
    @pytest.mark.asyncio
    async def test_broadcast_signal_partial_failure(self, agent_manager, sample_trade_signal, mock_httpx_client):
        """Test broadcasting signal with some agents failing"""
        # Register test agents
        agents = ["good-agent", "bad-agent"]
        for agent_id in agents:
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_id,
                endpoint=f"http://localhost:8001",
                status=AgentStatus.ACTIVE,
                last_seen=datetime.utcnow()
            )
            agent_manager.agents[agent_id] = agent_info
            agent_manager.health_status[agent_id] = AgentHealthStatus(
                agent_id=agent_id,
                status="healthy",
                last_seen=datetime.utcnow(),
                response_time_ms=100.0,
                error_count=0,
                success_rate=1.0
            )
        
        # Mock responses - good agent succeeds, bad agent fails
        def mock_post(url, *args, **kwargs):
            if "good-agent" in str(args) or "good-agent" in str(kwargs):
                response = Mock()
                response.status_code = 200
                response.json.return_value = {"success": True}
                return response
            else:
                response = Mock()
                response.status_code = 500
                return response
        
        mock_httpx_client.post.side_effect = mock_post
        
        results = await agent_manager.broadcast_signal(sample_trade_signal, agents)
        
        # Should only get results from the successful agent
        assert len(results) == 1
        assert "good-agent" in results
        assert "bad-agent" not in results
    
    @pytest.mark.asyncio
    async def test_get_healthy_agents(self, agent_manager):
        """Test getting healthy agents"""
        # Add mix of healthy and unhealthy agents
        agent_manager.health_status["healthy-1"] = AgentHealthStatus(
            agent_id="healthy-1", status="healthy", last_seen=datetime.utcnow(),
            response_time_ms=100.0, error_count=0, success_rate=1.0
        )
        agent_manager.health_status["healthy-2"] = AgentHealthStatus(
            agent_id="healthy-2", status="healthy", last_seen=datetime.utcnow(),
            response_time_ms=150.0, error_count=0, success_rate=0.9
        )
        agent_manager.health_status["unhealthy-1"] = AgentHealthStatus(
            agent_id="unhealthy-1", status="unhealthy", last_seen=datetime.utcnow(),
            response_time_ms=500.0, error_count=5, success_rate=0.3
        )
        
        healthy_agents = await agent_manager.get_healthy_agents()
        
        assert len(healthy_agents) == 2
        assert "healthy-1" in healthy_agents
        assert "healthy-2" in healthy_agents
        assert "unhealthy-1" not in healthy_agents
    
    @pytest.mark.asyncio
    async def test_health_check_loop_update(self, agent_manager, mock_httpx_client):
        """Test health check loop updates agent status"""
        # Register a test agent
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="test-agent",
            endpoint="http://localhost:8001",
            status=AgentStatus.ACTIVE,
            last_seen=datetime.utcnow() - timedelta(minutes=5)
        )
        agent_manager.agents["test-agent"] = agent_info
        agent_manager.health_status["test-agent"] = AgentHealthStatus(
            agent_id="test-agent",
            status="healthy",
            last_seen=datetime.utcnow() - timedelta(minutes=5),
            response_time_ms=100.0,
            error_count=0,
            success_rate=1.0
        )
        
        # Mock successful health check
        health_response = Mock()
        health_response.status_code = 200
        health_response.elapsed.total_seconds.return_value = 0.2
        mock_httpx_client.get.return_value = health_response
        
        # Run a single health check
        await agent_manager._check_agent_health("test-agent", agent_info)
        
        # Agent should still be active and health updated
        assert agent_info.status == AgentStatus.ACTIVE
        assert agent_manager.health_status["test-agent"].response_time_ms == 200.0  # 0.2s * 1000
    
    @pytest.mark.asyncio
    async def test_health_check_failure_handling(self, agent_manager, mock_httpx_client):
        """Test health check failure handling"""
        # Register a test agent
        agent_info = AgentInfo(
            agent_id="failing-agent",
            agent_type="failing-agent", 
            endpoint="http://localhost:8001",
            status=AgentStatus.ACTIVE,
            last_seen=datetime.utcnow()
        )
        agent_manager.agents["failing-agent"] = agent_info
        agent_manager.health_status["failing-agent"] = AgentHealthStatus(
            agent_id="failing-agent",
            status="healthy",
            last_seen=datetime.utcnow(),
            response_time_ms=100.0,
            error_count=0,
            success_rate=1.0
        )
        
        # Mock failed health check
        import httpx
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")
        
        # Run health check
        await agent_manager._check_agent_health("failing-agent", agent_info)
        
        # Agent should be marked as error and health updated
        assert agent_info.status == AgentStatus.ERROR
        assert agent_manager.health_status["failing-agent"].error_count > 0
        assert agent_manager.health_status["failing-agent"].success_rate < 1.0


class TestAgentHealthStatus:
    """Test AgentHealthStatus model"""
    
    def test_agent_health_status_creation(self):
        """Test creating AgentHealthStatus"""
        health = AgentHealthStatus(
            agent_id="test-agent",
            status="healthy",
            last_seen=datetime.utcnow(),
            response_time_ms=150.0,
            error_count=2,
            success_rate=0.85
        )
        
        assert health.agent_id == "test-agent"
        assert health.status == "healthy"
        assert health.response_time_ms == 150.0
        assert health.error_count == 2
        assert health.success_rate == 0.85


class TestAgentManagerIntegration:
    """Integration tests for AgentManager"""
    
    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(self, test_settings, mock_httpx_client):
        """Test full agent lifecycle: discovery -> health checks -> signal processing"""
        with patch('app.agent_manager.get_settings', return_value=test_settings):
            with patch('app.agent_manager.httpx.AsyncClient', return_value=mock_httpx_client):
                manager = AgentManager()
                
                try:
                    # Mock successful discovery
                    health_response = Mock()
                    health_response.status_code = 200
                    health_response.json.return_value = {"capabilities": ["trading"]}
                    health_response.elapsed.total_seconds.return_value = 0.1
                    mock_httpx_client.get.return_value = health_response
                    
                    # Start manager (should discover agents)
                    await manager.start()
                    assert len(manager.agents) == 8
                    
                    # Test signal processing
                    signal = TradeSignal(
                        id="test_123",
                        instrument="EUR_USD", 
                        direction="long",
                        confidence=0.85
                    )
                    
                    # Mock successful signal response
                    signal_response = Mock()
                    signal_response.status_code = 200
                    signal_response.json.return_value = {
                        "success": True,
                        "message": "Processed successfully"
                    }
                    mock_httpx_client.post.return_value = signal_response
                    
                    # Send signal to first agent
                    first_agent_id = list(manager.agents.keys())[0]
                    result = await manager.send_signal_to_agent(first_agent_id, signal)
                    
                    assert result.success is True
                    
                    # Test broadcasting
                    results = await manager.broadcast_signal(signal)
                    assert len(results) == len(manager.agents)
                    
                finally:
                    await manager.stop()