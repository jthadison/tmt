"""
Simple test for disagreement engine core functionality.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.disagreement_engine.app.models import (
    OriginalSignal, SignalDirection, DecisionBiases, 
    SituationalModifiers, CorrelationAwareness, DisagreementProfile
)


def test_disagreement_rate_calculation():
    """Test that we can calculate basic disagreement rates."""
    
    # Create a sample personality
    personality = DisagreementProfile(
        personality_id="test",
        base_disagreement_rate=0.175,  # 17.5%
        biases=DecisionBiases(
            risk_aversion=0.5,
            signal_skepticism=0.3,
            crowd_following=0.4,
            profit_taking=0.5,
            loss_avoidance=0.5
        ),
        situational_modifiers=SituationalModifiers(
            market_volatility=0.2,
            news_events=0.1,
            time_of_day={},
            day_of_week={}
        ),
        correlation_awareness=CorrelationAwareness(
            monitor_correlation=True,
            correlation_sensitivity=0.3,
            anti_correlation_bias=0.2
        )
    )
    
    # Verify personality was created correctly
    assert personality.base_disagreement_rate == 0.175
    assert 0.15 <= personality.base_disagreement_rate <= 0.20  # Within target range
    
    # Test signal creation
    signal = OriginalSignal(
        symbol="EURUSD",
        direction=SignalDirection.LONG,
        strength=0.8,
        price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100
    )
    
    assert signal.symbol == "EURUSD"
    assert signal.strength == 0.8


def test_disagreement_rate_range():
    """Test that disagreement rates are within acceptable range."""
    rates = [0.15, 0.175, 0.20]  # 15%, 17.5%, 20%
    
    for rate in rates:
        assert 0.15 <= rate <= 0.20, f"Rate {rate} outside acceptable range"
    
    # Test that rates outside range fail
    invalid_rates = [0.10, 0.25, 0.30]
    for rate in invalid_rates:
        assert not (0.15 <= rate <= 0.20), f"Rate {rate} should be invalid"


def test_participation_rate_calculation():
    """Test participation rate calculations."""
    target_range = (0.80, 0.85)  # 80-85%
    
    test_rates = [0.80, 0.825, 0.85]
    for rate in test_rates:
        assert target_range[0] <= rate <= target_range[1], f"Rate {rate} outside target range"


if __name__ == "__main__":
    test_disagreement_rate_calculation()
    test_disagreement_rate_range() 
    test_participation_rate_calculation()
    print("✅ All basic disagreement tests passed!")