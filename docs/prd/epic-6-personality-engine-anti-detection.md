# Epic 6: Personality Engine & Anti-Detection

Implement unique trading personalities and anti-correlation systems to avoid detection. This epic ensures the system appears as multiple independent human traders.

## Story 6.1: Trading Personality Generator

As a stealth system,
I want unique trading personalities per account,
so that each account appears as a different human trader.

### Acceptance Criteria

1: Personality profiles with preferred trading times, pairs, and risk levels
2: Personality traits: aggressive/conservative, morning/evening trader
3: Favorite pairs assignment (2-3 primary, 2-3 secondary per account)
4: Risk appetite variance (0.5%-2% per trade) per personality
5: Personality evolution over time simulating skill improvement
6: Personality configuration interface in dashboard

## Story 6.2: Execution Variance Engine

As an anti-detection system,
I want natural variance in trade execution,
so that patterns don't appear algorithmic.

### Acceptance Criteria

1: Entry timing variance of 1-30 seconds from signal generation
2: Position size rounding to human-friendly numbers (0.01, 0.05, 0.1 lots)
3: Stop loss/take profit placement with 1-3 pip variance
4: Occasional "missed" opportunities (5% of signals ignored)
5: Random micro-delays in order modifications (100-500ms)
6: Weekend behavior variance (some accounts trade Sunday open, others don't)

## Story 6.3: Decision Disagreement System

As a correlation masking system,
I want accounts to occasionally make different decisions,
so that they don't appear coordinated.

### Acceptance Criteria

1: 15-20% of signals result in different actions across accounts
2: Some accounts skip signals due to "personal" risk preferences
3: Entry timing spreads increased during high-signal periods
4: Different take profit levels based on personality "greed" factor
5: Disagreement logging showing rationale for variance
6: Correlation coefficient maintained below 0.7 between any two accounts

## Story 6.4: Human-Like Behavior Patterns

As a behavioral simulation system,
I want to replicate common human trading behaviors,
so that the system appears genuinely human.

### Acceptance Criteria

1: Gradual position size increases after winning streaks
2: Slightly reduced activity after losing days (risk aversion)
3: End-of-week position flattening for some personalities
4: Lunch break patterns for day-trader personalities
5: Occasional manual-looking adjustments to round numbers
6: Session preference consistency (London trader focuses on London session)

## Story 6.5: Anti-Pattern Detection Monitor

As a security system,
I want to monitor for detectable patterns,
so that I can adjust before prop firms identify automation.

### Acceptance Criteria

1: Pattern detection algorithm analyzing trade clustering
2: Execution precision monitoring (too perfect = suspicious)
3: Correlation tracking between accounts with alerts
4: Win rate consistency checks (too consistent = suspicious)
5: Timing pattern analysis for order placement
6: Monthly stealth report with recommendations for adjustment
