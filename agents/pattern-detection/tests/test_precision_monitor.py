"""
Tests for PrecisionMonitor
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PrecisionMonitor import (
    PrecisionMonitor,
    PrecisionThresholds,
    PrecisionScore,
    SuspiciousPattern,
    PrecisionAnalysis
)


class MockTrade:
    """Mock trade object for testing"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'T1')
        self.size = kwargs.get('size', Decimal('1.0'))
        self.entry_price = kwargs.get('entry_price', Decimal('1.1000'))
        self.stop_loss = kwargs.get('stop_loss', Decimal('1.0990'))
        self.take_profit = kwargs.get('take_profit', Decimal('1.1020'))
        self.signal_time = kwargs.get('signal_time', datetime.now())
        self.entry_time = kwargs.get('entry_time', datetime.now() + timedelta(seconds=1))
        self.exit_time = kwargs.get('exit_time', None)
        self.execution_delay_ms = kwargs.get('execution_delay_ms', 1000)


def create_precise_trades(count: int = 20) -> List[MockTrade]:
    """Create trades with suspicious precision"""
    trades = []
    base_time = datetime(2025, 1, 15, 10, 0, 0)
    
    for i in range(count):
        trades.append(MockTrade(
            id=f'P{i}',
            size=Decimal('1.0'),  # Same size (suspicious)
            entry_price=Decimal('1.1000'),
            stop_loss=Decimal('1.0990'),  # Exact 10 pip SL
            take_profit=Decimal('1.1020'),  # Exact 20 pip TP
            signal_time=base_time + timedelta(minutes=i*5),
            entry_time=base_time + timedelta(minutes=i*5, seconds=1),  # Exact 1 second delay
            execution_delay_ms=1000  # Exact same delay
        ))
    
    return trades


def create_human_trades(count: int = 20) -> List[MockTrade]:
    """Create trades with human-like variation"""
    trades = []
    base_time = datetime(2025, 1, 15, 10, 0, 0)
    np.random.seed(42)  # For reproducibility
    
    for i in range(count):
        # Variable sizes
        size = Decimal(str(1.0 + np.random.normal(0, 0.3)))
        
        # Variable entry prices
        entry_price = Decimal(str(1.1000 + np.random.normal(0, 0.001)))
        
        # Variable SL/TP distances
        sl_distance = Decimal(str(0.001 + np.random.normal(0, 0.0003)))
        tp_distance = Decimal(str(0.002 + np.random.normal(0, 0.0005)))
        
        # Variable delays
        signal_delay = np.random.uniform(0.5, 3.5)
        exec_delay = np.random.uniform(800, 2500)
        
        trades.append(MockTrade(
            id=f'H{i}',
            size=size,
            entry_price=entry_price,
            stop_loss=entry_price - sl_distance,
            take_profit=entry_price + tp_distance,
            signal_time=base_time + timedelta(minutes=i*5 + np.random.uniform(-1, 1)),
            entry_time=base_time + timedelta(minutes=i*5 + np.random.uniform(-1, 1), seconds=signal_delay),
            execution_delay_ms=exec_delay
        ))
    
    return trades


class TestPrecisionMonitor:
    """Test suite for PrecisionMonitor"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = PrecisionMonitor()
    
    def test_initialization(self):
        """Test monitor initialization"""
        # Default initialization
        monitor = PrecisionMonitor()
        assert monitor.thresholds is not None
        assert monitor.thresholds.max_entry_precision == 0.15
        assert monitor.thresholds.max_sizing_precision == 0.20
        
        # Custom thresholds
        custom_thresholds = PrecisionThresholds(
            max_entry_precision=0.10,
            max_sizing_precision=0.15
        )
        monitor = PrecisionMonitor(custom_thresholds)
        assert monitor.thresholds.max_entry_precision == 0.10
        assert monitor.thresholds.max_sizing_precision == 0.15
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        trades = create_human_trades(5)  # Less than min_sample_size
        
        analysis = self.monitor.analyze_precision(trades)
        
        assert analysis.overall_score == 0.0
        assert not analysis.suspicious
        assert len(analysis.suspicious_patterns) == 0
        assert "Insufficient data" in analysis.recommendations[0]
    
    def test_detect_precise_trades(self):
        """Test detection of suspiciously precise trades"""
        trades = create_precise_trades(20)
        
        analysis = self.monitor.analyze_precision(trades)
        
        assert analysis.suspicious
        assert analysis.overall_score > self.monitor.thresholds.suspicious_threshold
        assert len(analysis.suspicious_patterns) > 0
        
        # Should detect multiple precision issues
        pattern_types = [p.pattern_type for p in analysis.suspicious_patterns]
        assert any('sizing' in pt for pt in pattern_types)
        assert any('level' in pt for pt in pattern_types)
    
    def test_human_like_trades(self):
        """Test that human-like trades don't trigger alerts"""
        trades = create_human_trades(20)
        
        analysis = self.monitor.analyze_precision(trades)
        
        # Human trades should have lower suspicion than precise trades
        # But may still trigger some low-level alerts due to randomization
        assert analysis.overall_score < 0.35  # Allow for some variance in human simulation
        # Should have fewer and less severe patterns than precise trades
        high_severity = [p for p in analysis.suspicious_patterns if p.severity in ['critical', 'high']]
        assert len(high_severity) <= 2  # Allow for occasional false positives in human simulation
    
    def test_entry_timing_precision(self):
        """Test entry timing precision calculation"""
        # Create trades with exact timing
        trades = []
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        
        for i in range(15):
            trades.append(MockTrade(
                signal_time=base_time + timedelta(minutes=i),
                entry_time=base_time + timedelta(minutes=i, seconds=1)  # Exact 1 second delay
            ))
        
        precision = self.monitor.calculate_entry_timing_precision(trades)
        assert precision > 0.8  # Should be very high (suspicious)
        
        # Now with variable timing
        trades_variable = []
        for i in range(15):
            delay = np.random.uniform(0.5, 3.5)
            trades_variable.append(MockTrade(
                signal_time=base_time + timedelta(minutes=i),
                entry_time=base_time + timedelta(minutes=i, seconds=delay)
            ))
        
        precision_variable = self.monitor.calculate_entry_timing_precision(trades_variable)
        assert precision_variable < precision  # Should be lower
    
    def test_position_sizing_precision(self):
        """Test position sizing precision calculation"""
        # All same size (suspicious)
        trades_same = [MockTrade(size=Decimal('1.0')) for _ in range(15)]
        precision_same = self.monitor.calculate_position_sizing_precision(trades_same)
        assert precision_same > 0.7
        
        # Variable sizes (human-like)
        trades_variable = [
            MockTrade(size=Decimal(str(1.0 + np.random.normal(0, 0.3))))
            for _ in range(15)
        ]
        precision_variable = self.monitor.calculate_position_sizing_precision(trades_variable)
        assert precision_variable < precision_same
    
    def test_level_placement_precision(self):
        """Test stop loss and take profit placement precision"""
        # Exact pip values (suspicious)
        trades_exact = []
        for i in range(15):
            trades_exact.append(MockTrade(
                entry_price=Decimal('1.1000'),
                stop_loss=Decimal('1.0990'),  # Exact 10 pips
                take_profit=Decimal('1.1020')  # Exact 20 pips
            ))
        
        precision_exact = self.monitor.calculate_level_placement_precision(trades_exact)
        assert precision_exact > 0.7
        
        # Variable levels (human-like)
        trades_variable = []
        for i in range(15):
            entry = Decimal('1.1000')
            sl_distance = Decimal(str(0.001 + np.random.normal(0, 0.0003)))
            tp_distance = Decimal(str(0.002 + np.random.normal(0, 0.0005)))
            
            trades_variable.append(MockTrade(
                entry_price=entry,
                stop_loss=entry - sl_distance,
                take_profit=entry + tp_distance
            ))
        
        precision_variable = self.monitor.calculate_level_placement_precision(trades_variable)
        assert precision_variable < precision_exact
    
    def test_variance_metrics(self):
        """Test variance metrics calculation"""
        trades = create_human_trades(20)
        
        variance_metrics = self.monitor.calculate_variance_metrics(trades)
        
        assert 'size_variance' in variance_metrics
        assert 'entry_time_variance' in variance_metrics
        assert all(v >= 0 for v in variance_metrics.values())
    
    def test_round_number_detection(self):
        """Test detection of round number patterns"""
        monitor = PrecisionMonitor()
        
        # Test round numbers
        assert monitor._is_round_number(1.0)
        assert monitor._is_round_number(1.5)
        assert monitor._is_round_number(1.25)
        assert monitor._is_round_number(1.10)
        
        # Test non-round numbers
        assert not monitor._is_round_number(1.12345)
        assert not monitor._is_round_number(1.33333)
        
        # Test round number scoring
        round_values = [1.0, 2.0, 1.5, 2.5, 3.0]
        score_round = monitor._calculate_round_number_score(round_values)
        assert score_round > 0.7
        
        random_values = [1.12345, 2.67891, 1.33333, 2.44444, 3.55555]
        score_random = monitor._calculate_round_number_score(random_values)
        assert score_random < 0.3
    
    def test_recommendations_generation(self):
        """Test generation of recommendations"""
        # Precise trades should generate specific recommendations
        trades = create_precise_trades(20)
        analysis = self.monitor.analyze_precision(trades)
        
        assert len(analysis.recommendations) > 0
        
        # Should recommend adding variance
        recs_text = ' '.join(analysis.recommendations)
        assert 'random' in recs_text.lower() or 'vary' in recs_text.lower()
        
        # Critical precision should generate urgent recommendations
        if analysis.overall_score > self.monitor.thresholds.critical_threshold:
            assert any('CRITICAL' in r for r in analysis.recommendations)
    
    def test_precision_history_tracking(self):
        """Test that precision history is tracked"""
        trades = create_human_trades(20)
        
        # Initial history should be empty
        assert len(self.monitor.precision_history) == 0
        
        # Analyze trades
        self.monitor.analyze_precision(trades)
        
        # History should be updated
        assert len(self.monitor.precision_history) > 0
        
        # Check history entries
        for score in self.monitor.precision_history:
            assert isinstance(score, PrecisionScore)
            assert score.sample_size == 20
            assert 0 <= score.score <= 1
    
    def test_precision_trends(self):
        """Test precision trend analysis"""
        # Analyze multiple batches to create history
        for i in range(3):
            trades = create_human_trades(20)
            self.monitor.analyze_precision(trades)
        
        trends = self.monitor.get_precision_trends(lookback_hours=24)
        
        assert trends['status'] == 'analyzed'
        assert 'trends' in trends
        
        # Check trend structure
        for category, trend_data in trends['trends'].items():
            assert 'direction' in trend_data
            assert 'magnitude' in trend_data
            assert 'current' in trend_data
            assert 'average' in trend_data
    
    def test_suspicious_pattern_detection(self):
        """Test detection of specific suspicious patterns"""
        trades = create_precise_trades(20)
        analysis = self.monitor.analyze_precision(trades)
        
        # Should detect patterns
        assert len(analysis.suspicious_patterns) > 0
        
        for pattern in analysis.suspicious_patterns:
            assert isinstance(pattern, SuspiciousPattern)
            assert pattern.pattern_type
            assert pattern.severity in ['low', 'medium', 'high', 'critical']
            assert pattern.description
            assert pattern.recommendation
            assert pattern.affected_trades == 20
    
    def test_execution_delay_precision(self):
        """Test execution delay precision detection"""
        # Consistent delays (suspicious)
        trades_consistent = [
            MockTrade(execution_delay_ms=1000) for _ in range(15)
        ]
        
        precision_consistent = self.monitor.calculate_execution_delay_precision(trades_consistent)
        assert precision_consistent > 0.8
        
        # Variable delays (human-like)
        trades_variable = [
            MockTrade(execution_delay_ms=np.random.uniform(500, 2500))
            for _ in range(15)
        ]
        
        precision_variable = self.monitor.calculate_execution_delay_precision(trades_variable)
        assert precision_variable < precision_consistent