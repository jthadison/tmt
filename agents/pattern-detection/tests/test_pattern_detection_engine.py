"""
Tests for PatternDetectionEngine
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PatternDetectionEngine import PatternDetectionEngine, DetectionThresholds, PatternAlert, StealthReport


class MockTrade:
    """Mock trade object for testing"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'T1')
        self.account_id = kwargs.get('account_id', 'ACC001')
        self.symbol = kwargs.get('symbol', 'EURUSD')
        self.timestamp = kwargs.get('timestamp', datetime.now())
        self.entry_time = kwargs.get('entry_time', self.timestamp)
        self.exit_time = kwargs.get('exit_time', self.timestamp + timedelta(minutes=30))
        self.size = kwargs.get('size', Decimal('1.0'))
        self.direction = kwargs.get('direction', 'long')
        self.entry_price = kwargs.get('entry_price', Decimal('1.1000'))
        self.exit_price = kwargs.get('exit_price', Decimal('1.1010'))
        self.stop_loss = kwargs.get('stop_loss', Decimal('1.0990'))
        self.take_profit = kwargs.get('take_profit', Decimal('1.1020'))
        self.signal_time = kwargs.get('signal_time', self.timestamp - timedelta(seconds=1))
        self.execution_delay_ms = kwargs.get('execution_delay_ms', 1000)
        self.pnl = kwargs.get('pnl', float(self.exit_price - self.entry_price))


def create_suspicious_account_trades(num_accounts: int = 3, trades_per_account: int = 25) -> dict:
    """Create suspicious trading patterns across multiple accounts"""
    account_trades = {}
    base_time = datetime.now() - timedelta(days=7)
    
    for acc_idx in range(num_accounts):
        account_id = f'ACC{acc_idx:03d}'
        trades = []
        
        for i in range(trades_per_account):
            # Create suspicious patterns
            # - Same timing patterns
            trade_time = base_time + timedelta(hours=i*2)
            
            # - Similar sizes 
            size = Decimal('1.0')  # All same size
            
            # - Precise levels
            entry = Decimal('1.1000')
            sl = Decimal('1.0990')  # Exact 10 pips
            tp = Decimal('1.1020')  # Exact 20 pips
            
            # - High win rate (too consistent)
            is_winner = i % 10 < 7  # 70% win rate consistently
            exit_price = tp if is_winner else sl
            pnl = float(exit_price - entry)  # Assume long direction
            
            trades.append(MockTrade(
                id=f'{account_id}_T{i}',
                account_id=account_id,
                timestamp=trade_time,
                entry_time=trade_time + timedelta(seconds=1),  # Exact 1 second delay
                exit_time=trade_time + timedelta(minutes=30),  # Exact 30 min duration
                size=size,
                entry_price=entry,
                exit_price=exit_price,
                stop_loss=sl,
                take_profit=tp,
                signal_time=trade_time,
                execution_delay_ms=1000,  # Exact same delay
                pnl=pnl
            ))
        
        account_trades[account_id] = trades
    
    return account_trades


def create_human_like_account_trades(num_accounts: int = 3, trades_per_account: int = 25) -> dict:
    """Create human-like trading patterns with natural variation"""
    account_trades = {}
    base_time = datetime.now() - timedelta(days=7)
    np.random.seed(42)  # For reproducibility
    
    for acc_idx in range(num_accounts):
        account_id = f'HUM{acc_idx:03d}'
        trades = []
        
        for i in range(trades_per_account):
            # Variable timing
            trade_time = base_time + timedelta(
                hours=i*2 + np.random.uniform(-0.5, 0.5),
                minutes=np.random.uniform(0, 30)
            )
            
            # Variable sizes
            size = Decimal(str(max(0.1, 1.0 + np.random.normal(0, 0.3))))
            
            # Variable levels
            entry = Decimal(str(1.1000 + np.random.normal(0, 0.001)))
            sl_distance = Decimal(str(0.001 + np.random.normal(0, 0.0003)))
            tp_distance = Decimal(str(0.002 + np.random.normal(0, 0.0005)))
            
            # Variable win rate
            is_winner = np.random.random() < (0.6 + np.random.normal(0, 0.1))  # Variable win rate
            
            # Variable delays and durations
            signal_delay = np.random.uniform(0.5, 3.5)
            duration = np.random.uniform(15, 180)
            exec_delay = np.random.uniform(800, 2500)
            
            exit_price = entry + tp_distance if is_winner else entry - sl_distance
            pnl = float(exit_price - entry) * float(size)
            
            trades.append(MockTrade(
                id=f'{account_id}_T{i}',
                account_id=account_id,
                timestamp=trade_time,
                entry_time=trade_time + timedelta(seconds=signal_delay),
                exit_time=trade_time + timedelta(minutes=duration),
                size=size,
                entry_price=entry,
                exit_price=exit_price,
                stop_loss=entry - sl_distance,
                take_profit=entry + tp_distance,
                signal_time=trade_time,
                execution_delay_ms=exec_delay,
                pnl=pnl
            ))
        
        account_trades[account_id] = trades
    
    return account_trades


class TestPatternDetectionEngine:
    """Test suite for PatternDetectionEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = PatternDetectionEngine()
    
    def test_initialization(self):
        """Test engine initialization"""
        engine = PatternDetectionEngine()
        
        assert engine.clustering_detector is not None
        assert engine.precision_monitor is not None
        assert engine.correlation_tracker is not None
        assert engine.consistency_checker is not None
        assert len(engine.active_alerts) == 0
        assert len(engine.analysis_history) == 0
    
    def test_suspicious_patterns_detection(self):
        """Test detection of suspicious patterns across all components"""
        # Create suspicious trading data
        suspicious_trades = create_suspicious_account_trades(3, 30)
        
        # Analyze patterns
        results = self.engine.analyze_patterns(suspicious_trades)
        
        # Should detect moderate to high risk (suspicious patterns exist)
        assert results['overall_risk_score'] > 0.15
        
        # Should generate alerts
        assert len(results['alerts']) > 0
        
        # Should detect multiple pattern types
        alert_types = set(alert.alert_type for alert in results['alerts'])
        assert len(alert_types) >= 2  # Multiple detection types
        
        # Should have recommendations
        assert len(results['recommendations']) > 0
        
        # Component analyses should be present
        assert 'clustering' in results
        assert 'precision' in results
        assert 'correlation' in results
        assert 'consistency' in results
    
    def test_human_like_patterns_acceptance(self):
        """Test that human-like patterns don't trigger false alarms"""
        # Create human-like trading data
        human_trades = create_human_like_account_trades(3, 30)
        
        # Analyze patterns
        results = self.engine.analyze_patterns(human_trades)
        
        # Should have low risk
        assert results['overall_risk_score'] < 0.4
        
        # Should have few or no critical alerts
        critical_alerts = [a for a in results['alerts'] if a.severity == 'critical']
        assert len(critical_alerts) <= 1
    
    def test_overall_risk_calculation(self):
        """Test overall risk score calculation"""
        # Mock analysis results
        mock_results = {
            'clustering': type('obj', (object,), {'risk_score': 0.3})(),
            'precision': type('obj', (object,), {'overall_score': 0.2})(),
            'correlation': type('obj', (object,), {'risk_score': 0.7})(),
            'consistency': type('obj', (object,), {'overall_consistency_score': 0.1})()
        }
        
        risk_score = self.engine.calculate_overall_risk(mock_results)
        
        # Should be weighted average
        expected = (0.3 * 0.25) + (0.2 * 0.20) + (0.7 * 0.30) + (0.1 * 0.25)
        assert abs(risk_score - expected) < 0.01
    
    def test_stealth_report_generation(self):
        """Test stealth report generation"""
        # Create test data
        account_trades = create_suspicious_account_trades(2, 20)
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # Generate report
        report = self.engine.generate_stealth_report(
            start_date, end_date, account_trades
        )
        
        # Verify report structure
        assert isinstance(report, StealthReport)
        assert report.report_id.startswith('STEALTH_')
        assert report.period == (start_date, end_date)
        assert 0 <= report.stealth_score <= 100
        assert report.risk_level in ['low', 'medium', 'high', 'critical']
        assert len(report.executive_summary) > 0
        assert len(report.recommendations) > 0
        assert len(report.priority_actions) > 0
        assert report.stealth_trend in ['improving', 'stable', 'degrading']
    
    def test_alert_generation(self):
        """Test unified alert generation"""
        # Create data that should trigger alerts
        suspicious_trades = create_suspicious_account_trades(2, 25)
        
        # Analyze patterns
        results = self.engine.analyze_patterns(suspicious_trades)
        
        alerts = results['alerts']
        assert len(alerts) > 0
        
        # Check alert structure
        for alert in alerts:
            assert isinstance(alert, PatternAlert)
            assert alert.id
            assert alert.alert_type in ['clustering', 'precision', 'correlation', 'consistency', 'timing']
            assert alert.severity in ['low', 'medium', 'high', 'critical']
            assert alert.description
            assert 0 <= alert.risk_level <= 1
            assert len(alert.recommended_actions) > 0
            assert alert.urgency in ['immediate', 'within_24h', 'within_week']
    
    def test_analysis_history_tracking(self):
        """Test that analysis history is properly tracked"""
        account_trades = create_human_like_account_trades(2, 15)
        
        # Initial history should be empty
        assert len(self.engine.analysis_history) == 0
        
        # Perform analysis
        self.engine.analyze_patterns(account_trades)
        
        # History should be updated
        assert len(self.engine.analysis_history) == 1
        
        # Perform another analysis
        self.engine.analyze_patterns(account_trades)
        
        # History should have both analyses
        assert len(self.engine.analysis_history) == 2
    
    def test_consolidated_recommendations(self):
        """Test consolidated recommendation generation"""
        # Mock analysis results with recommendations
        mock_results = {
            'clustering': type('obj', (object,), {
                'recommendations': ['Add random delays', 'CRITICAL: Immediate action']
            })(),
            'precision': type('obj', (object,), {
                'recommendations': ['Increase variance', 'HIGH: Adjust precision']
            })(),
            'correlation': type('obj', (object,), {
                'recommendations': ['Desynchronize accounts', 'Add random delays']  # Duplicate
            })(),
            'consistency': type('obj', (object,), {
                'recommendations': ['Vary performance', 'MEDIUM: Monitor closely']
            })()
        }
        
        recommendations = self.engine._generate_consolidated_recommendations(mock_results)
        
        # Should prioritize by urgency
        assert recommendations[0].startswith('CRITICAL')
        
        # Should deduplicate
        delay_recs = [r for r in recommendations if 'random delays' in r]
        assert len(delay_recs) == 1  # Should be deduplicated
        
        # Should limit to reasonable number
        assert len(recommendations) <= 10
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data scenarios"""
        # Empty data
        empty_trades = {}
        results = self.engine.analyze_patterns(empty_trades)
        
        assert results['overall_risk_score'] == 0.0
        assert len(results['alerts']) == 0
        
        # Single account with few trades
        minimal_trades = {'ACC001': [MockTrade() for _ in range(3)]}
        results = self.engine.analyze_patterns(minimal_trades)
        
        # Should handle gracefully without errors
        assert 'error' not in results
        assert results['overall_risk_score'] >= 0.0
    
    def test_custom_thresholds(self):
        """Test engine with custom thresholds"""
        # Create more sensitive thresholds
        custom_thresholds = DetectionThresholds()
        custom_thresholds.precision.max_entry_precision = 0.05  # Very sensitive
        custom_thresholds.correlation.warning_threshold = 0.3  # Very sensitive
        
        engine = PatternDetectionEngine(custom_thresholds)
        
        # Even human-like data should trigger with very sensitive thresholds
        human_trades = create_human_like_account_trades(2, 20)
        results = engine.analyze_patterns(human_trades)
        
        # Should be more sensitive than default
        default_results = self.engine.analyze_patterns(human_trades)
        
        # Custom engine should detect more issues (higher risk or more alerts)
        assert (results['overall_risk_score'] >= default_results['overall_risk_score'] or
                len(results['alerts']) >= len(default_results['alerts']))
    
    def test_error_handling(self):
        """Test error handling in analysis pipeline"""
        # Create malformed trade data
        malformed_trades = {
            'ACC001': [
                type('BadTrade', (), {})()  # Missing required attributes
            ]
        }
        
        # Should handle gracefully
        results = self.engine.analyze_patterns(malformed_trades)
        
        # Should not crash and should indicate some form of handling
        assert isinstance(results, dict)
        assert 'timestamp' in results