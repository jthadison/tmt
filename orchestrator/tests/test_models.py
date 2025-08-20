"""
Tests for Trading System Orchestrator Models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    TradeSignal, TradeResult, AgentStatus, AgentInfo,
    SystemStatus, SystemMetrics, CircuitBreakerStatus,
    TradingParameters, DisagreementResult
)


class TestTradeSignal:
    """Test TradeSignal model"""
    
    def test_valid_trade_signal(self):
        """Test creating a valid trade signal"""
        signal = TradeSignal(
            id="test_123",
            instrument="EUR_USD",
            direction="long",
            confidence=0.85,
            entry_price=1.0500,
            stop_loss=1.0450,
            take_profit=1.0600,
            risk_reward_ratio=2.0,
            timeframe="H1"
        )
        
        assert signal.id == "test_123"
        assert signal.instrument == "EUR_USD"
        assert signal.direction == "long"
        assert signal.confidence == 0.85
        assert signal.entry_price == 1.0500
        assert signal.risk_reward_ratio == 2.0
        assert isinstance(signal.timestamp, datetime)
    
    def test_invalid_confidence_range(self):
        """Test that confidence must be between 0 and 1"""
        with pytest.raises(ValidationError):
            TradeSignal(
                id="test_123",
                instrument="EUR_USD",
                direction="long",
                confidence=1.5  # Invalid - greater than 1
            )
        
        with pytest.raises(ValidationError):
            TradeSignal(
                id="test_123",
                instrument="EUR_USD",
                direction="long",
                confidence=-0.1  # Invalid - less than 0
            )
    
    def test_invalid_direction(self):
        """Test that direction must be 'long' or 'short'"""
        with pytest.raises(ValidationError):
            TradeSignal(
                id="test_123",
                instrument="EUR_USD",
                direction="buy",  # Invalid - must be 'long' or 'short'
                confidence=0.85
            )
    
    def test_metadata_field(self):
        """Test that metadata field works correctly"""
        metadata = {
            "volume_analysis": "high",
            "smart_money_flow": "bullish",
            "confluence_score": 8.5
        }
        
        signal = TradeSignal(
            id="test_123",
            instrument="EUR_USD",
            direction="long",
            confidence=0.85,
            metadata=metadata
        )
        
        assert signal.metadata == metadata
        assert signal.metadata["confluence_score"] == 8.5


class TestTradeResult:
    """Test TradeResult model"""
    
    def test_successful_trade_result(self):
        """Test creating a successful trade result"""
        result = TradeResult(
            success=True,
            signal_id="test_123",
            trade_id="67890",
            executed_price=1.0500,
            executed_units=1000.0,
            pnl=50.0,
            commission=2.50,
            financing=0.25,
            message="Trade executed successfully"
        )
        
        assert result.success is True
        assert result.signal_id == "test_123"
        assert result.trade_id == "67890"
        assert result.executed_price == 1.0500
        assert result.pnl == 50.0
        assert isinstance(result.execution_time, datetime)
    
    def test_failed_trade_result(self):
        """Test creating a failed trade result"""
        result = TradeResult(
            success=False,
            signal_id="test_123",
            message="Insufficient margin"
        )
        
        assert result.success is False
        assert result.signal_id == "test_123"
        assert result.message == "Insufficient margin"
        assert result.trade_id is None
        assert result.executed_price is None


class TestAgentInfo:
    """Test AgentInfo model"""
    
    def test_valid_agent_info(self):
        """Test creating valid agent info"""
        agent = AgentInfo(
            agent_id="market-analysis",
            agent_type="market-analysis",
            endpoint="http://localhost:8001",
            status=AgentStatus.ACTIVE,
            last_seen=datetime.utcnow(),
            capabilities=["signal_generation", "market_analysis"],
            version="1.0.0"
        )
        
        assert agent.agent_id == "market-analysis"
        assert agent.status == AgentStatus.ACTIVE
        assert "signal_generation" in agent.capabilities
        assert agent.version == "1.0.0"
    
    def test_agent_status_enum(self):
        """Test AgentStatus enum values"""
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.INACTIVE == "inactive"
        assert AgentStatus.ERROR == "error"
        assert AgentStatus.STARTING == "starting"
        assert AgentStatus.STOPPING == "stopping"


class TestSystemStatus:
    """Test SystemStatus model"""
    
    def test_system_status_creation(self):
        """Test creating system status"""
        circuit_breaker_status = CircuitBreakerStatus(
            overall_status="closed",
            can_trade=True
        )
        
        status = SystemStatus(
            running=True,
            trading_enabled=True,
            uptime_seconds=3600,
            connected_agents=8,
            total_agents=8,
            circuit_breaker_status=circuit_breaker_status,
            oanda_connection=True,
            last_update=datetime.utcnow(),
            system_health="healthy"
        )
        
        assert status.running is True
        assert status.connected_agents == 8
        assert status.system_health == "healthy"
        assert status.circuit_breaker_status.can_trade is True


class TestSystemMetrics:
    """Test SystemMetrics model"""
    
    def test_system_metrics_creation(self):
        """Test creating system metrics"""
        metrics = SystemMetrics(
            signals_processed=150,
            trades_executed=75,
            total_pnl=2500.50,
            win_rate=0.65,
            average_latency=45.2,
            uptime_seconds=86400,
            memory_usage_mb=512.0,
            cpu_usage_percent=25.5
        )
        
        assert metrics.signals_processed == 150
        assert metrics.trades_executed == 75
        assert metrics.total_pnl == 2500.50
        assert metrics.win_rate == 0.65
        assert metrics.average_latency == 45.2


class TestTradingParameters:
    """Test TradingParameters model"""
    
    def test_trading_parameters_creation(self):
        """Test creating trading parameters"""
        params = TradingParameters(
            position_size=1000.0,
            stop_loss_pips=50.0,
            take_profit_pips=100.0,
            risk_amount=200.0,
            max_risk_percent=0.02,
            confidence_threshold=0.75,
            account_allocation={"account_1": 0.5, "account_2": 0.5}
        )
        
        assert params.position_size == 1000.0
        assert params.max_risk_percent == 0.02
        assert params.confidence_threshold == 0.75
        assert params.account_allocation["account_1"] == 0.5


class TestDisagreementResult:
    """Test DisagreementResult model"""
    
    def test_disagreement_result_approved(self):
        """Test approved disagreement result"""
        result = DisagreementResult(
            approved=True,
            timing_adjustments={"account_1": 5, "account_2": 0},
            position_adjustments={"account_1": 0.8, "account_2": 1.0},
            correlation_score=0.3,
            reason="Low correlation, approved with adjustments"
        )
        
        assert result.approved is True
        assert result.timing_adjustments["account_1"] == 5
        assert result.position_adjustments["account_1"] == 0.8
        assert result.correlation_score == 0.3
    
    def test_disagreement_result_rejected(self):
        """Test rejected disagreement result"""
        result = DisagreementResult(
            approved=False,
            correlation_score=0.95,
            reason="High correlation detected, trade rejected"
        )
        
        assert result.approved is False
        assert result.correlation_score == 0.95
        assert "High correlation" in result.reason


class TestModelValidation:
    """Test model validation and edge cases"""
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            TradeSignal()  # Missing required fields
        
        with pytest.raises(ValidationError):
            AgentInfo(agent_id="test")  # Missing other required fields
    
    def test_default_values(self):
        """Test default values are set correctly"""
        signal = TradeSignal(
            id="test_123",
            instrument="EUR_USD",
            direction="long",
            confidence=0.85
        )
        
        # Check that timestamp is set to current time
        assert isinstance(signal.timestamp, datetime)
        
        # Check that metadata defaults to empty dict
        assert signal.metadata == {}
        
        # Check that optional fields are None
        assert signal.entry_price is None
        assert signal.stop_loss is None
    
    def test_field_types(self):
        """Test that field types are validated correctly"""
        with pytest.raises(ValidationError):
            TradeSignal(
                id=123,  # Should be string
                instrument="EUR_USD",
                direction="long",
                confidence=0.85
            )
        
        with pytest.raises(ValidationError):
            TradeResult(
                success="yes",  # Should be boolean
                message="Test"
            )
    
    def test_json_serialization(self):
        """Test that models can be serialized to JSON"""
        signal = TradeSignal(
            id="test_123",
            instrument="EUR_USD",
            direction="long",
            confidence=0.85,
            metadata={"test": "value"}
        )
        
        # Should not raise an exception
        json_data = signal.model_dump()
        
        assert json_data["id"] == "test_123"
        assert json_data["confidence"] == 0.85
        assert json_data["metadata"]["test"] == "value"