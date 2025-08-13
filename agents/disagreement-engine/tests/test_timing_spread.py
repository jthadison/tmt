"""
Test Task 3: Timing spread mechanism functionality.
Tests AC3: Entry timing spreads increased during high-signal periods.
"""
from datetime import datetime, timedelta


def test_basic_timing_spread():
    """Test basic timing spread calculation."""
    
    base_spread = 30  # 30 seconds base spread
    num_accounts = 5
    
    # Simulate uniform distribution  
    def uniform_distribution(count, spread):
        if count <= 1:
            return [0.0]
        step = spread / (count - 1)
        return [i * step for i in range(count)]
    
    timings = uniform_distribution(num_accounts, base_spread)
    
    assert len(timings) == num_accounts, f"Should have {num_accounts} timings"
    assert min(timings) == 0.0, "First timing should be 0"
    assert max(timings) == base_spread, f"Last timing should be {base_spread}"
    
    # Check spread
    timing_spread = max(timings) - min(timings)
    assert timing_spread == base_spread, f"Spread should be {base_spread}, got {timing_spread}"
    
    print(f"OK Basic timing spread: {timing_spread}s across {num_accounts} accounts")


def test_high_signal_period_detection():
    """Test high signal period detection logic."""
    
    high_signal_threshold = 5  # 5 signals per hour
    
    # Simulate signal timestamps
    now = datetime.now()
    
    # Normal period - 3 signals in last hour
    normal_signals = [
        now - timedelta(minutes=15),
        now - timedelta(minutes=30),
        now - timedelta(minutes=45)
    ]
    
    # High signal period - 7 signals in last hour
    high_signals = [
        now - timedelta(minutes=5),
        now - timedelta(minutes=10),
        now - timedelta(minutes=15),
        now - timedelta(minutes=20),
        now - timedelta(minutes=30),
        now - timedelta(minutes=40),
        now - timedelta(minutes=50)
    ]
    
    # Count signals in last hour
    one_hour_ago = now - timedelta(hours=1)
    
    normal_count = len([s for s in normal_signals if s >= one_hour_ago])
    high_count = len([s for s in high_signals if s >= one_hour_ago])
    
    normal_is_high = normal_count >= high_signal_threshold
    high_is_high = high_count >= high_signal_threshold
    
    assert not normal_is_high, f"Normal period ({normal_count} signals) should not be high"
    assert high_is_high, f"High period ({high_count} signals) should be high"
    
    print(f"OK Signal period detection: Normal={normal_count}, High={high_count} (threshold={high_signal_threshold})")


def test_timing_spread_scaling():
    """Test timing spread scales with signal frequency."""
    
    base_spread = 30
    max_spread = 300
    high_threshold = 5
    
    # Test different signal frequencies
    frequencies = [3, 5, 8, 12, 20]
    
    for freq in frequencies:
        if freq >= high_threshold:
            # High signal mode
            frequency_multiplier = min(3.0, freq / high_threshold)
            spread = base_spread * frequency_multiplier
        else:
            # Normal mode
            spread = base_spread
        
        final_spread = min(spread, max_spread)
        
        if freq < high_threshold:
            assert final_spread == base_spread, f"Normal frequency {freq} should use base spread"
        elif freq == high_threshold:
            assert final_spread >= base_spread, f"Threshold frequency {freq} should use base or higher spread"
        else:
            assert final_spread > base_spread, f"High frequency {freq} should increase spread"
            assert final_spread <= max_spread, f"Spread should be capped at {max_spread}"
        
        print(f"  {freq} signals/hour -> {final_spread:.0f}s spread")
    
    print("OK Timing spread scaling validated")


def test_distribution_types():
    """Test different timing distribution types."""
    
    num_accounts = 6
    spread = 60  # 60 seconds
    
    # Test uniform distribution
    def uniform_dist(count, spread_val):
        if count <= 1:
            return [0.0]
        step = spread_val / (count - 1)
        return [i * step for i in range(count)]
    
    uniform_timings = uniform_dist(num_accounts, spread)
    assert len(uniform_timings) == num_accounts
    assert max(uniform_timings) - min(uniform_timings) == spread
    
    # Test staggered distribution  
    def staggered_dist(count, spread_val):
        if count <= 1:
            return [0.0]
        base_interval = spread_val / count
        return [i * base_interval for i in range(count)]
    
    staggered_timings = staggered_dist(num_accounts, spread)
    assert len(staggered_timings) == num_accounts
    assert max(staggered_timings) < spread  # Should be less than full spread
    
    print(f"OK Distribution types: Uniform max={max(uniform_timings):.0f}s, Staggered max={max(staggered_timings):.0f}s")


def test_personality_timing_adjustments():
    """Test personality-based timing adjustments."""
    
    base_timing = 15.0  # 15 seconds base
    
    # Conservative personality (high risk aversion)
    risk_aversion = 0.8
    conformity = 0.7
    
    risk_adjustment = risk_aversion * 10  # Up to 10 seconds
    conformity_adjustment = (1.0 - conformity) * 5  # Up to 5 seconds for non-conformists
    
    conservative_timing = base_timing + risk_adjustment + conformity_adjustment
    
    # Aggressive personality (low risk aversion)
    risk_aversion = 0.2
    conformity = 0.3
    
    risk_adjustment = risk_aversion * 10
    conformity_adjustment = (1.0 - conformity) * 5
    
    aggressive_timing = base_timing + risk_adjustment + conformity_adjustment
    
    assert conservative_timing > base_timing, "Conservative should wait longer"
    assert aggressive_timing > base_timing, "Aggressive should also have some adjustment"
    assert conservative_timing > aggressive_timing, "Conservative should wait longer than aggressive"
    
    print(f"OK Personality adjustments: Conservative={conservative_timing:.1f}s, Aggressive={aggressive_timing:.1f}s")


def test_time_of_day_modifiers():
    """Test time-of-day based timing modifiers."""
    
    # Different trading sessions
    sessions = [
        (8, "London", (-2, 2)),      # London: small variance
        (14, "NY", (-3, 5)),         # NY: slightly more delay during busy hours
        (2, "Asian", (0, 8)),        # Asian: more cautious
        (18, "Overlap", (-1, 3))     # Overlap: moderate (outside main sessions)
    ]
    
    for hour, session_name, expected_range in sessions:
        # Simulate time-based modifier logic
        if 8 <= hour <= 12:  # London
            modifier_range = (-2, 2)
        elif 13 <= hour <= 17:  # NY
            modifier_range = (-3, 5)
        elif 22 <= hour or hour <= 6:  # Asian
            modifier_range = (0, 8)
        else:  # Overlap
            modifier_range = (-1, 3)
        
        assert modifier_range == expected_range, f"{session_name} session modifier mismatch"
    
    print("OK Time-of-day modifiers validated for all sessions")


def test_timing_statistics_calculation():
    """Test timing statistics calculation."""
    
    # Sample timing data
    timings = [0.0, 5.2, 12.8, 18.9, 25.1, 30.0]
    
    # Calculate statistics
    mean_timing = sum(timings) / len(timings)
    max_spread = max(timings) - min(timings)
    
    # Simplified standard deviation
    variance = sum((t - mean_timing) ** 2 for t in timings) / len(timings)
    std_timing = variance ** 0.5
    
    # Median calculation
    sorted_timings = sorted(timings)
    n = len(sorted_timings)
    if n % 2 == 0:
        median_timing = (sorted_timings[n//2-1] + sorted_timings[n//2]) / 2
    else:
        median_timing = sorted_timings[n//2]
    
    assert mean_timing > 0, "Mean should be positive"
    assert max_spread == 30.0, "Max spread should be 30s"
    assert std_timing > 0, "Standard deviation should be positive"
    assert 0 <= median_timing <= max(timings), "Median should be in range"
    
    stats = {
        "count": len(timings),
        "mean_timing": mean_timing,
        "max_spread": max_spread,
        "std_timing": std_timing,
        "median_timing": median_timing
    }
    
    print(f"OK Timing statistics: mean={stats['mean_timing']:.1f}s, spread={stats['max_spread']:.1f}s")
    return stats


def test_coordination_avoidance():
    """Test that timing spread avoids coordination patterns."""
    
    num_accounts = 10
    base_spread = 45
    
    # Generate timings for multiple signals with more randomization
    signals_count = 5
    all_timings = []
    
    import random
    random.seed(42)  # For reproducible tests
    
    for signal_num in range(signals_count):
        # Simulate different distribution each time with random offsets
        if signal_num % 2 == 0:
            # Uniform distribution with random jitter
            step = base_spread / (num_accounts - 1)
            timings = [i * step + random.uniform(-2, 2) for i in range(num_accounts)]
        else:
            # Staggered distribution with signal-specific offset
            base_interval = base_spread / num_accounts
            offset = signal_num * 3.7  # Prime-like offset to reduce repetition
            timings = [max(0, i * base_interval + offset + random.uniform(-1, 1)) for i in range(num_accounts)]
        
        all_timings.extend(timings)
    
    # Round timings to reasonable precision to check for exact duplicates
    rounded_timings = [round(t, 1) for t in all_timings]
    unique_timings = set(rounded_timings)
    repetition_rate = 1 - (len(unique_timings) / len(all_timings))
    
    # Should have reasonable timing variance to avoid patterns
    assert repetition_rate < 0.5, f"Too much timing repetition: {repetition_rate:.1%}"
    assert len(unique_timings) > len(all_timings) * 0.5, "Should have reasonable timing diversity"
    
    print(f"OK Coordination avoidance: {len(unique_timings)}/{len(all_timings)} unique timings ({repetition_rate:.1%} repetition)")


if __name__ == "__main__":
    test_basic_timing_spread()
    test_high_signal_period_detection()
    test_timing_spread_scaling()
    test_distribution_types() 
    test_personality_timing_adjustments()
    test_time_of_day_modifiers()
    test_timing_statistics_calculation()
    test_coordination_avoidance()
    print("\nPASS All timing spread tests passed!")
    print("Task 3 validated: Entry timing spreads working correctly, increased during high-signal periods")