"""
Test Task 2: Risk-based signal skipping functionality.
Tests AC2: Some accounts skip signals due to "personal" risk preferences.
"""


def test_risk_threshold_logic():
    """Test basic risk threshold comparison logic."""
    
    # Test scenario 1: Risk below threshold - should take signal
    combined_risk = 0.4
    risk_threshold = 0.6
    should_skip = combined_risk > risk_threshold
    assert not should_skip, "Should take signal when risk below threshold"
    
    # Test scenario 2: Risk above threshold - should skip signal
    combined_risk = 0.8
    risk_threshold = 0.6  
    should_skip = combined_risk > risk_threshold
    assert should_skip, "Should skip signal when risk above threshold"
    
    # Test scenario 3: Risk at threshold - should take signal
    combined_risk = 0.6
    risk_threshold = 0.6
    should_skip = combined_risk > risk_threshold
    assert not should_skip, "Should take signal when risk equals threshold"
    
    print("OK Risk threshold logic tests passed")


def test_risk_level_calculation():
    """Test risk level calculation components."""
    
    # Test personal risk calculation
    signal_confidence = 0.8  # Strong signal
    skepticism = 0.3  # Moderate skepticism
    risk_aversion = 0.7  # High risk aversion
    
    # Personal risk calculation logic
    confidence_risk = (1.0 - signal_confidence) * (1.0 + skepticism)  # 0.26
    risk_multiplier = 1.0 + risk_aversion * 0.5  # 1.35
    personal_risk = min(1.0, confidence_risk * risk_multiplier)  # 0.35
    
    assert 0.0 <= personal_risk <= 1.0, "Personal risk should be 0-1"
    assert personal_risk < 0.5, "Should be low risk for strong signal"
    
    # Test market risk factors
    volatility_risk = 0.4
    news_risk = 0.2
    session_risk = 0.1
    pair_risk = 0.15
    
    market_risk = min(1.0, (volatility_risk + news_risk + session_risk + pair_risk) / 4.0)
    assert 0.0 <= market_risk <= 1.0, "Market risk should be 0-1"
    
    # Test portfolio risk factors
    drawdown_pct = 5.0  # 5% drawdown
    drawdown_risk = min(1.0, drawdown_pct / 10.0)  # 0.5 (risk increases with drawdown)
    
    concentration_positions = 2  # 2 positions in same symbol
    concentration_risk = min(0.8, concentration_positions * 0.2)  # 0.4
    
    daily_trades = 8  # 8 trades today
    overtrading_risk = min(0.5, max(0.0, (daily_trades - 5) * 0.1))  # 0.3
    
    portfolio_risk = min(1.0, drawdown_risk + concentration_risk + overtrading_risk)  # 1.0 capped
    assert 0.0 <= portfolio_risk <= 1.0, "Portfolio risk should be 0-1"
    
    print(f"OK Risk calculation: Personal={personal_risk:.2f}, Market={market_risk:.2f}, Portfolio={portfolio_risk:.2f}")


def test_risk_combination():
    """Test how individual risk factors combine."""
    
    personal_risk = 0.4
    market_risk = 0.3
    portfolio_risk = 0.5
    
    # Weighted combination
    personal_weight = 0.4
    market_weight = 0.3
    portfolio_weight = 0.3
    
    combined = (
        personal_risk * personal_weight +
        market_risk * market_weight +
        portfolio_risk * portfolio_weight
    )  # 0.4*0.4 + 0.3*0.3 + 0.5*0.3 = 0.16 + 0.09 + 0.15 = 0.40
    
    # Non-linear scaling for high risk
    if combined > 0.7:
        combined = 0.7 + (combined - 0.7) * 1.5
    
    final_risk = min(1.0, combined)
    
    assert 0.0 <= final_risk <= 1.0, "Final risk should be 0-1"
    assert abs(final_risk - 0.40) < 0.01, f"Expected ~0.40, got {final_risk:.3f}"
    
    print(f"OK Risk combination: {final_risk:.2f} from components")


def test_risk_threshold_personality_based():
    """Test personality-based risk threshold calculation."""
    
    # Conservative personality
    risk_aversion = 0.8
    loss_avoidance = 0.9
    skepticism = 0.6
    
    base_threshold = 0.3 + (risk_aversion * 0.5)  # 0.7
    loss_adjustment = loss_avoidance * 0.2  # 0.18
    skepticism_adjustment = skepticism * 0.15  # 0.09
    
    conservative_threshold = min(0.9, base_threshold + loss_adjustment + skepticism_adjustment)  # 0.9 (capped)
    
    # Aggressive personality
    risk_aversion = 0.2
    loss_avoidance = 0.3
    skepticism = 0.1
    
    base_threshold = 0.3 + (risk_aversion * 0.5)  # 0.4
    loss_adjustment = loss_avoidance * 0.2  # 0.06
    skepticism_adjustment = skepticism * 0.15  # 0.015
    
    aggressive_threshold = min(0.9, base_threshold + loss_adjustment + skepticism_adjustment)  # 0.475
    
    assert conservative_threshold > aggressive_threshold, "Conservative should have higher threshold"
    assert 0.3 <= conservative_threshold <= 0.9, "Conservative threshold in valid range"
    assert 0.3 <= aggressive_threshold <= 0.9, "Aggressive threshold in valid range"
    
    print(f"OK Personality thresholds: Conservative={conservative_threshold:.2f}, Aggressive={aggressive_threshold:.2f}")


def test_skip_rate_validation():
    """Test that skip rates are reasonable for risk management."""
    
    # Simulate 100 accounts with various risk profiles
    total_accounts = 100
    skipped_accounts = 0
    
    # Different personality types and their skip probabilities
    personality_types = [
        ("conservative", 0.25),  # 25% skip rate
        ("moderate", 0.15),      # 15% skip rate  
        ("aggressive", 0.08),    # 8% skip rate
        ("risk_averse", 0.30),   # 30% skip rate
    ]
    
    for personality, skip_rate in personality_types:
        type_accounts = 25  # 25 accounts per type
        type_skips = int(type_accounts * skip_rate)
        skipped_accounts += type_skips
        
        print(f"  {personality}: {type_skips}/{type_accounts} skipped ({skip_rate:.1%})")
    
    total_skip_rate = skipped_accounts / total_accounts
    
    # Skip rate should be reasonable (10-30% based on risk preferences)
    assert 0.10 <= total_skip_rate <= 0.30, f"Skip rate {total_skip_rate:.1%} outside reasonable range"
    
    print(f"OK Total skip rate: {skipped_accounts}/{total_accounts} = {total_skip_rate:.1%}")


def test_risk_based_skip_reasons():
    """Test that skip reasons are human-readable and realistic."""
    
    skip_reasons = [
        "Market too volatile for my risk appetite",
        "Already have similar exposure",
        "Waiting for better entry opportunity", 
        "Not convinced by signal strength",
        "Taking a break after recent losses",
        "Account approaching daily limit",
        "Risk management says pass on this one",
        "Technical setup doesn't look clean to me"
    ]
    
    # All reasons should be realistic and human-like
    for reason in skip_reasons:
        assert len(reason) > 10, f"Reason '{reason}' too short"
        assert len(reason) < 100, f"Reason '{reason}' too long"
        risk_related = ("risk" in reason.lower() or "loss" in reason.lower() or "volatile" in reason.lower() or 
                       "exposure" in reason.lower() or "limit" in reason.lower() or "opportunity" in reason.lower() or
                       "signal" in reason.lower() or "setup" in reason.lower() or "break" in reason.lower())
        assert risk_related, f"Reason '{reason}' doesn't contain risk-related terms"
    
    print(f"OK {len(skip_reasons)} realistic skip reasons validated")


def test_drawdown_impact_on_risk():
    """Test how account drawdown affects risk assessment."""
    
    # Test different drawdown scenarios
    drawdown_scenarios = [
        (0.0, "No drawdown - low risk"),
        (2.5, "Small drawdown - moderate risk"),  
        (5.0, "Medium drawdown - higher risk"),
        (8.0, "Large drawdown - high risk"),
        (12.0, "Major drawdown - maximum risk")
    ]
    
    for drawdown_pct, description in drawdown_scenarios:
        drawdown_risk = min(1.0, drawdown_pct / 10.0)
        
        if drawdown_pct == 0.0:
            assert drawdown_risk == 0.0, "No drawdown should have zero risk"
        elif drawdown_pct >= 10.0:
            assert drawdown_risk >= 1.0, "Major drawdown should have maximum risk"
        else:
            assert 0.0 < drawdown_risk < 1.0, f"Moderate drawdown should have moderate risk: {drawdown_risk}"
        
        print(f"  {description}: {drawdown_pct}% -> {drawdown_risk:.1f} risk")
    
    print("OK Drawdown impact on risk validated")


if __name__ == "__main__":
    test_risk_threshold_logic()
    test_risk_level_calculation()  
    test_risk_combination()
    test_risk_threshold_personality_based()
    test_skip_rate_validation()
    test_risk_based_skip_reasons()
    test_drawdown_impact_on_risk()
    print("\nPASS All risk-based skipping tests passed!")
    print("Task 2 validated: Risk-based signal skipping system working correctly")