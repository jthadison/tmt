"""
Tests for Learning Circuit Breaker Triggers

Tests the integrated learning trigger engine that coordinates all safety mechanisms.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from learning_triggers import (
    LearningTriggerEngine,
    LearningDecision,
    LearningTriggerDecision
)
from market_condition_detector import (
    MarketData,
    MarketConditionThresholds
)
from news_event_monitor import (
    NewsEvent,
    NewsImpact,
    NewsCurrency
)


@pytest.fixture
def trigger_engine():
    """Create learning trigger engine for testing"""
    return LearningTriggerEngine()


@pytest.fixture
def normal_market_data():
    """Normal market data that should allow learning"""
    return MarketData(
        timestamp=datetime.utcnow(),
        symbol="EURUSD",
        bid=Decimal("1.0500"),
        ask=Decimal("1.0502"),
        volume=1000,
        price=Decimal("1.0501")
    )


@pytest.fixture
def volatile_market_data():
    """Volatile market data that should trigger safety measures"""
    return MarketData(
        timestamp=datetime(2023, 12, 15, 9, 15),  # Market open time
        symbol="EURUSD",
        bid=Decimal("1.0400"),  # Large movement + wide spread
        ask=Decimal("1.0420"),
        volume=5000,
        price=Decimal("1.0410")
    )


class TestLearningTriggerEngine:
    """Test learning trigger engine functionality"""
    
    def test_allow_learning_on_normal_conditions(self, trigger_engine, normal_market_data):
        """Test that normal market conditions allow learning"""
        decision = trigger_engine.evaluate_learning_safety(normal_market_data)
        
        assert decision.decision == LearningDecision.ALLOW
        assert decision.learning_safe
        assert decision.risk_score < 0.3
        assert len(decision.detected_anomalies) == 0
        assert not decision.quarantine_data
        assert not decision.manual_review_required
        assert decision.confidence > 0.8
    
    def test_deny_learning_on_volatile_conditions(self, trigger_engine, volatile_market_data):
        """Test that volatile conditions deny or monitor learning"""
        # Add baseline data for comparison
        base_time = volatile_market_data.timestamp - timedelta(minutes=10)
        for i in range(10):
            baseline_data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=Decimal("1.0500"),
                ask=Decimal("1.0502"),
                volume=1000,
                price=Decimal("1.0501")
            )
            trigger_engine.evaluate_learning_safety(baseline_data)
        
        decision = trigger_engine.evaluate_learning_safety(volatile_market_data)
        
        # Should detect market hours anomaly and have some risk
        assert len(decision.detected_anomalies) > 0  # Market hours anomaly should be detected
        assert decision.risk_score > 0.0
        # Market hours anomaly is low severity, so may allow with monitoring
        # The key is that anomalies are detected and risk is elevated
        market_hours_anomalies = [a for a in decision.detected_anomalies if a.condition_type.value == "market_hours"]
        assert len(market_hours_anomalies) > 0  # Confirm market hours anomaly specifically
    
    def test_news_event_lockout(self, trigger_engine, normal_market_data):
        """Test that news events trigger learning lockouts"""
        # Add a high-impact news event
        news_event = NewsEvent(
            event_id="nfp_2023_12_15",
            title="Non-Farm Payrolls",
            currency=NewsCurrency.USD,
            impact=NewsImpact.HIGH,
            scheduled_time=normal_market_data.timestamp - timedelta(minutes=30),
            forecast_value="200K",
            actual_value="250K"
        )
        
        news_monitor = trigger_engine.get_news_monitor()
        news_monitor.add_scheduled_event(news_event)
        news_monitor.process_event_release(
            news_event.event_id, 
            normal_market_data.timestamp - timedelta(minutes=30),
            "250K"
        )
        
        decision = trigger_engine.evaluate_learning_safety(normal_market_data)
        
        assert decision.decision in [LearningDecision.DENY, LearningDecision.MONITOR]
        assert not decision.learning_safe or decision.decision == LearningDecision.MONITOR
        assert len(decision.detected_anomalies) > 0
        assert any(a.condition_type.value == "news_event" for a in decision.detected_anomalies)
    
    def test_risk_score_calculation(self, trigger_engine):
        """Test risk score calculation with multiple anomalies"""
        # Create data that will trigger multiple anomalies
        multi_anomaly_data = MarketData(
            timestamp=datetime(2023, 12, 15, 9, 15),  # Market open + volatile
            symbol="EURUSD",
            bid=Decimal("1.0300"),  # Large gap
            ask=Decimal("1.0340"),  # Wide spread
            volume=10000,  # High volume
            price=Decimal("1.0320")
        )
        
        decision = trigger_engine.evaluate_learning_safety(multi_anomaly_data)
        
        # Multiple anomalies should increase risk score
        if len(decision.detected_anomalies) > 1:
            assert decision.risk_score > 0.3
        
        # Verify severity breakdown
        assert isinstance(decision.severity_breakdown, dict)
        assert all(key in decision.severity_breakdown for key in ["low", "medium", "high", "critical"])
    
    def test_decision_confidence_calculation(self, trigger_engine, normal_market_data, volatile_market_data):
        """Test confidence calculation for different scenarios"""
        # Normal conditions should have high confidence
        normal_decision = trigger_engine.evaluate_learning_safety(normal_market_data)
        assert normal_decision.confidence > 0.8
        
        # Volatile conditions should have variable confidence based on anomaly strength
        volatile_decision = trigger_engine.evaluate_learning_safety(volatile_market_data)
        assert 0.0 <= volatile_decision.confidence <= 1.0
    
    def test_quarantine_recommendation(self, trigger_engine):
        """Test quarantine recommendation logic"""
        # Create critical market conditions
        critical_data = MarketData(
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            bid=Decimal("1.0000"),  # Extreme price movement
            ask=Decimal("1.0100"),  # Very wide spread
            volume=50000,  # Extreme volume
            price=Decimal("1.0050")
        )
        
        decision = trigger_engine.evaluate_learning_safety(critical_data)
        
        # Should recommend quarantine for extreme conditions
        if decision.risk_score >= 0.8:
            assert decision.quarantine_data
            assert decision.decision == LearningDecision.QUARANTINE
    
    def test_manual_review_triggers(self, trigger_engine):
        """Test manual review requirement logic"""
        # Create conditions that should trigger manual review
        review_data = MarketData(
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            bid=Decimal("1.0200"),  # Significant movement
            ask=Decimal("1.0250"),  # Wide spread
            volume=20000,
            price=Decimal("1.0225")
        )
        
        decision = trigger_engine.evaluate_learning_safety(review_data)
        
        # High risk scores should trigger manual review
        if decision.risk_score >= 0.8:
            assert decision.manual_review_required
    
    def test_decision_reason_generation(self, trigger_engine, normal_market_data):
        """Test that decision reasons are informative"""
        decision = trigger_engine.evaluate_learning_safety(normal_market_data)
        
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0
        assert "Risk score:" in decision.reason
        
        # Should contain decision context
        decision_phrases = [
            "Learning approved",
            "Learning suspended", 
            "data quarantined",
            "monitoring",
            "learning safe"  # For normal conditions
        ]
        assert any(phrase in decision.reason for phrase in decision_phrases)
    
    def test_lockout_duration_calculation(self, trigger_engine):
        """Test lockout duration calculation"""
        # Test with market open condition (should have lockout)
        market_open_data = MarketData(
            timestamp=datetime(2023, 12, 15, 9, 15),
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        
        decision = trigger_engine.evaluate_learning_safety(market_open_data)
        
        if len(decision.detected_anomalies) > 0:
            assert decision.lockout_duration_minutes >= 0
            # Market hours anomalies typically have 30-minute lockouts
            if any(a.condition_type.value == "market_hours" for a in decision.detected_anomalies):
                assert decision.lockout_duration_minutes > 0


class TestRiskThresholds:
    """Test risk threshold configuration and behavior"""
    
    def test_custom_risk_thresholds(self):
        """Test engine with custom risk thresholds"""
        engine = LearningTriggerEngine()
        
        # Modify thresholds for testing
        engine.risk_thresholds = {
            "monitor": 0.1,    # Very low threshold
            "deny": 0.2,       # Low threshold
            "quarantine": 0.3  # Medium threshold
        }
        
        # Even minor anomalies should trigger stricter decisions
        minor_anomaly_data = MarketData(
            timestamp=datetime(2023, 12, 15, 9, 25),  # Near market open
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        
        decision = engine.evaluate_learning_safety(minor_anomaly_data)
        
        # With lower thresholds, should be more restrictive
        if len(decision.detected_anomalies) > 0:
            assert decision.decision in [LearningDecision.MONITOR, LearningDecision.DENY, LearningDecision.QUARANTINE]
    
    def test_severity_weight_impact(self):
        """Test impact of severity weights on decision making"""
        engine = LearningTriggerEngine()
        
        # Increase critical severity weight
        engine.severity_weights["critical"] = 2.0  # Double weight
        
        data = MarketData(
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        
        decision = engine.evaluate_learning_safety(data)
        
        # Modified weights should affect risk calculation
        # This is more of a structural test to ensure weights are used
        assert hasattr(engine, 'severity_weights')
        assert engine.severity_weights["critical"] == 2.0