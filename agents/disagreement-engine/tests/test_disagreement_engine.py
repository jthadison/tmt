"""
Test suite for DisagreementEngine - Core disagreement logic testing.
Tests AC1: 15-20% of signals result in different actions across accounts.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import Dict, List

from agents.disagreement_engine.app.disagreement_engine import DisagreementEngine
from agents.disagreement_engine.app.models import (
    OriginalSignal, SignalDirection, DecisionType, DisagreementProfile,
    DecisionBiases, SituationalModifiers, CorrelationAwareness
)


@pytest.fixture
def mock_correlation_monitor():
    """Mock correlation monitor."""
    monitor = Mock()
    monitor.get_current_correlations.return_value = {
        "account1_account2": 0.3,
        "account1_account3": 0.4,
        "account2_account3": 0.5
    }
    return monitor


@pytest.fixture
def mock_risk_engine():
    """Mock risk assessment engine."""
    engine = Mock()
    return engine


@pytest.fixture
def mock_decision_generator():
    """Mock decision generator."""
    generator = Mock()
    return generator


@pytest.fixture
def disagreement_engine(mock_correlation_monitor, mock_risk_engine, mock_decision_generator):
    """Create DisagreementEngine with mocked dependencies."""
    return DisagreementEngine(
        correlation_monitor=mock_correlation_monitor,
        risk_engine=mock_risk_engine,
        decision_generator=mock_decision_generator
    )


@pytest.fixture
def sample_signal():
    """Sample trading signal."""
    return OriginalSignal(
        symbol="EURUSD",
        direction=SignalDirection.LONG,
        strength=0.8,
        price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100
    )


@pytest.fixture
def sample_accounts():
    """Sample account configurations."""
    return [
        {"id": "account1", "personality_id": "conservative", "base_position_size": 0.01},
        {"id": "account2", "personality_id": "aggressive", "base_position_size": 0.02},
        {"id": "account3", "personality_id": "moderate", "base_position_size": 0.015},
        {"id": "account4", "personality_id": "contrarian", "base_position_size": 0.012},
        {"id": "account5", "personality_id": "risk_averse", "base_position_size": 0.008}
    ]


@pytest.fixture
def sample_personalities():
    """Sample personality profiles."""
    return {
        "conservative": DisagreementProfile(
            personality_id="conservative",
            base_disagreement_rate=0.15,
            biases=DecisionBiases(
                risk_aversion=0.8,
                signal_skepticism=0.6,
                crowd_following=0.7,
                profit_taking=0.8,
                loss_avoidance=0.9
            ),
            situational_modifiers=SituationalModifiers(
                market_volatility=0.3,
                news_events=0.2,
                time_of_day={},
                day_of_week={}
            ),
            correlation_awareness=CorrelationAwareness(
                monitor_correlation=True,
                correlation_sensitivity=0.5,
                anti_correlation_bias=0.3
            )
        ),
        "aggressive": DisagreementProfile(
            personality_id="aggressive",
            base_disagreement_rate=0.18,
            biases=DecisionBiases(
                risk_aversion=0.2,
                signal_skepticism=0.1,
                crowd_following=0.3,
                profit_taking=0.2,
                loss_avoidance=0.3
            ),
            situational_modifiers=SituationalModifiers(
                market_volatility=0.1,
                news_events=0.05,
                time_of_day={},
                day_of_week={}
            ),
            correlation_awareness=CorrelationAwareness(
                monitor_correlation=True,
                correlation_sensitivity=0.2,
                anti_correlation_bias=0.1
            )
        )
    }


class TestDisagreementEngine:
    """Test cases for DisagreementEngine."""

    def test_initialization(self, disagreement_engine):
        """Test engine initialization."""
        assert disagreement_engine.target_disagreement_rate == (0.15, 0.20)
        assert disagreement_engine.target_participation_rate == (0.80, 0.85)
        assert disagreement_engine.correlation_window == 100

    def test_calculate_participation_rate_base(self, disagreement_engine, sample_signal, sample_accounts, sample_personalities):
        """Test participation rate calculation."""
        participation_rate = disagreement_engine._calculate_participation_rate(
            sample_signal, sample_accounts, sample_personalities
        )
        
        # Should be within target range
        assert 0.6 <= participation_rate <= 0.95
        
    def test_calculate_participation_rate_signal_strength_adjustment(self, disagreement_engine, sample_accounts, sample_personalities):
        """Test participation rate adjusts based on signal strength."""
        # Strong signal should increase participation
        strong_signal = OriginalSignal(
            symbol="EURUSD", direction=SignalDirection.LONG,
            strength=0.95, price=1.1000, stop_loss=1.0950, take_profit=1.1100
        )
        
        strong_participation = disagreement_engine._calculate_participation_rate(
            strong_signal, sample_accounts, sample_personalities
        )
        
        # Weak signal should decrease participation
        weak_signal = OriginalSignal(
            symbol="EURUSD", direction=SignalDirection.LONG,
            strength=0.1, price=1.1000, stop_loss=1.0950, take_profit=1.1100
        )
        
        weak_participation = disagreement_engine._calculate_participation_rate(
            weak_signal, sample_accounts, sample_personalities
        )
        
        # Strong signal should generally have higher participation
        assert strong_participation >= weak_participation - 0.1  # Allow some randomness

    def test_select_participants(self, disagreement_engine, sample_accounts):
        """Test participant selection."""
        participation_rate = 0.6  # 60% should participate
        
        participants = disagreement_engine._select_participants(sample_accounts, participation_rate)
        
        expected_count = int(len(sample_accounts) * participation_rate)
        assert len(participants) == expected_count
        
        # Should be subset of original accounts
        for participant in participants:
            assert participant in sample_accounts

    def test_adjust_for_correlation_no_high_correlation(self, disagreement_engine, mock_correlation_monitor):
        """Test correlation adjustment when no high correlations exist."""
        # Mock low correlations
        mock_correlation_monitor.get_current_correlations.return_value = {
            "account1_account2": 0.3,
            "account1_account3": 0.4
        }
        
        # Mock decisions
        from agents.disagreement_engine.app.models import AccountDecision, RiskAssessment, PersonalityFactors, SignalModifications
        
        decisions = [
            AccountDecision(
                account_id="account1", personality_id="test",
                decision=DecisionType.TAKE, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        ]
        
        sample_signal = OriginalSignal(
            symbol="EURUSD", direction=SignalDirection.LONG,
            strength=0.8, price=1.1000, stop_loss=1.0950, take_profit=1.1100
        )
        
        result = disagreement_engine._adjust_for_correlation(decisions, sample_signal)
        
        # Should return unchanged when no high correlations
        assert len(result) == len(decisions)
        assert result[0].decision == DecisionType.TAKE

    def test_adjust_for_correlation_high_correlation_forces_disagreement(self, disagreement_engine, mock_correlation_monitor):
        """Test that high correlation forces disagreement."""
        # Mock high correlation
        mock_correlation_monitor.get_current_correlations.return_value = {
            "account1_account2": 0.75  # Above 0.65 threshold
        }
        
        from agents.disagreement_engine.app.models import AccountDecision, RiskAssessment, PersonalityFactors, SignalModifications
        
        # Both accounts initially taking signal
        decisions = [
            AccountDecision(
                account_id="account1", personality_id="test",
                decision=DecisionType.TAKE, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            ),
            AccountDecision(
                account_id="account2", personality_id="test",
                decision=DecisionType.TAKE, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        ]
        
        sample_signal = OriginalSignal(
            symbol="EURUSD", direction=SignalDirection.LONG,
            strength=0.8, price=1.1000, stop_loss=1.0950, take_profit=1.1100
        )
        
        result = disagreement_engine._adjust_for_correlation(decisions, sample_signal)
        
        # One of the decisions should be forced to disagree
        take_decisions = [d for d in result if d.decision == DecisionType.TAKE]
        disagreement_decisions = [d for d in result if d.decision != DecisionType.TAKE]
        
        assert len(take_decisions) == 1
        assert len(disagreement_decisions) == 1

    def test_calculate_disagreement_metrics_empty_decisions(self, disagreement_engine, sample_signal):
        """Test metrics calculation with empty decisions."""
        metrics = disagreement_engine._calculate_disagreement_metrics([], sample_signal)
        
        assert metrics.participation_rate == 0.0
        assert metrics.direction_consensus == 0.0
        assert metrics.timing_spread == 0.0

    def test_calculate_disagreement_metrics_with_decisions(self, disagreement_engine, sample_signal):
        """Test metrics calculation with actual decisions."""
        from agents.disagreement_engine.app.models import AccountDecision, RiskAssessment, PersonalityFactors, SignalModifications
        
        decisions = [
            # Taking decisions
            AccountDecision(
                account_id="account1", personality_id="test",
                decision=DecisionType.TAKE, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications(timing=5.0, take_profit=1.1150)
            ),
            AccountDecision(
                account_id="account2", personality_id="test",
                decision=DecisionType.MODIFY, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications(timing=15.0, take_profit=1.1080)
            ),
            # Skipping decision
            AccountDecision(
                account_id="account3", personality_id="test",
                decision=DecisionType.SKIP, reasoning="test",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.8, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.8,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        ]
        
        metrics = disagreement_engine._calculate_disagreement_metrics(decisions, sample_signal)
        
        # 2 out of 3 participating (TAKE + MODIFY)
        assert metrics.participation_rate == 2/3
        
        # Direction consensus should be 1.0 (all participants going same direction)
        assert metrics.direction_consensus == 1.0
        
        # Timing spread should be 15 - 5 = 10 seconds
        assert metrics.timing_spread == 10.0
        
        # Profit target spread should be 1.1150 - 1.1080 = 0.007
        assert abs(metrics.profit_target_spread - 0.007) < 0.001

    def test_validate_disagreement_rate_within_range(self, disagreement_engine):
        """Test disagreement rate validation when in range."""
        # Mock signal disagreements with 17% disagreement rate (within 15-20%)
        mock_signals = []
        
        # Create mock signals data
        for i in range(10):  # 10 signals
            mock_signal = Mock()
            mock_signal.account_decisions = []
            
            # Add 10 decisions per signal, 8 take, 2 disagree = 20% disagreement
            for j in range(8):
                decision = Mock()
                decision.decision = DecisionType.TAKE
                mock_signal.account_decisions.append(decision)
            
            for j in range(2):
                decision = Mock()
                decision.decision = DecisionType.SKIP
                mock_signal.account_decisions.append(decision)
            
            mock_signals.append(mock_signal)
        
        result = disagreement_engine.validate_disagreement_rate(mock_signals)
        
        assert result["disagreement_rate"] == 0.2  # 20%
        assert result["in_range"] is True
        assert result["total_signals"] == 10
        assert result["total_decisions"] == 100
        assert result["total_disagreements"] == 20

    def test_validate_disagreement_rate_out_of_range(self, disagreement_engine):
        """Test disagreement rate validation when out of range."""
        # Mock signals with 30% disagreement rate (above 20%)
        mock_signals = []
        
        for i in range(10):
            mock_signal = Mock()
            mock_signal.account_decisions = []
            
            # 7 take, 3 disagree = 30% disagreement
            for j in range(7):
                decision = Mock()
                decision.decision = DecisionType.TAKE
                mock_signal.account_decisions.append(decision)
            
            for j in range(3):
                decision = Mock()
                decision.decision = DecisionType.SKIP
                mock_signal.account_decisions.append(decision)
            
            mock_signals.append(mock_signal)
        
        result = disagreement_engine.validate_disagreement_rate(mock_signals)
        
        assert result["disagreement_rate"] == 0.3  # 30%
        assert result["in_range"] is False

    def test_generate_disagreements_integration(self, disagreement_engine, mock_decision_generator, 
                                              sample_signal, sample_accounts, sample_personalities):
        """Integration test for complete disagreement generation."""
        from agents.disagreement_engine.app.models import AccountDecision, RiskAssessment, PersonalityFactors, SignalModifications
        
        # Mock decision generator to return predictable decisions
        def mock_generate_decision(signal, account, personality):
            return AccountDecision(
                account_id=account["id"],
                personality_id=personality.personality_id,
                decision=DecisionType.TAKE,
                reasoning="Test decision",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        
        def mock_generate_skip_decision(signal, account, personality):
            return AccountDecision(
                account_id=account["id"],
                personality_id=personality.personality_id if personality else "default",
                decision=DecisionType.SKIP,
                reasoning="Test skip",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.8, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.8,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        
        mock_decision_generator.generate_account_decision.side_effect = mock_generate_decision
        mock_decision_generator.generate_skip_decision.side_effect = mock_generate_skip_decision
        
        result = disagreement_engine.generate_disagreements(
            signal=sample_signal,
            accounts=sample_accounts,
            personalities=sample_personalities,
            signal_id="test-signal-1"
        )
        
        # Verify structure
        assert result.signal_id == "test-signal-1"
        assert result.original_signal == sample_signal
        assert len(result.account_decisions) == len(sample_accounts)
        assert result.disagreement_metrics is not None
        assert result.correlation_impact is not None
        
        # Verify participation rate is calculated
        assert 0.0 <= result.disagreement_metrics.participation_rate <= 1.0


class TestDisagreementEngineErrorHandling:
    """Test error handling in DisagreementEngine."""

    def test_missing_personality_uses_default(self, disagreement_engine, mock_decision_generator,
                                            sample_signal, sample_accounts):
        """Test handling of missing personality profiles."""
        from agents.disagreement_engine.app.models import AccountDecision, RiskAssessment, PersonalityFactors, SignalModifications
        
        # Empty personalities dict
        personalities = {}
        
        def mock_generate_decision(signal, account, personality):
            return AccountDecision(
                account_id=account["id"],
                personality_id=personality.personality_id,
                decision=DecisionType.TAKE,
                reasoning="Test decision",
                risk_assessment=RiskAssessment(
                    personal_risk_level=0.3, market_risk_level=0.2,
                    portfolio_risk_level=0.1, combined_risk_level=0.2,
                    risk_threshold=0.5
                ),
                personality_factors=PersonalityFactors(
                    greed_factor=0.5, fear_factor=0.5, impatience_level=0.5,
                    conformity_level=0.5, contrarian=False
                ),
                modifications=SignalModifications()
            )
        
        mock_decision_generator.generate_account_decision.side_effect = mock_generate_decision
        
        # Should not raise exception
        result = disagreement_engine.generate_disagreements(
            signal=sample_signal,
            accounts=sample_accounts[:1],  # Just one account for simplicity
            personalities=personalities,
            signal_id="test-signal-missing-personality"
        )
        
        assert result.signal_id == "test-signal-missing-personality"
        assert len(result.account_decisions) <= len(sample_accounts[:1])  # May skip some

    def test_empty_accounts_list(self, disagreement_engine, sample_signal, sample_personalities):
        """Test handling of empty accounts list."""
        result = disagreement_engine.generate_disagreements(
            signal=sample_signal,
            accounts=[],
            personalities=sample_personalities,
            signal_id="test-signal-no-accounts"
        )
        
        assert result.signal_id == "test-signal-no-accounts"
        assert len(result.account_decisions) == 0
        assert result.disagreement_metrics.participation_rate == 0.0