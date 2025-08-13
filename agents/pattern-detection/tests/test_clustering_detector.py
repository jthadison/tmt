"""
Tests for ClusteringDetector
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ClusteringDetector import (
    ClusteringDetector,
    ClusteringThresholds,
    Trade,
    TemporalCluster,
    SymbolCluster,
    SynchronizationEvent,
    ClusteringAnalysis
)


def create_test_trade(
    trade_id: str,
    account_id: str = "ACC001",
    symbol: str = "EURUSD",
    timestamp: datetime = None,
    size: Decimal = Decimal("1.0")
) -> Trade:
    """Helper to create test trades"""
    if timestamp is None:
        timestamp = datetime.now()
    
    return Trade(
        id=trade_id,
        account_id=account_id,
        symbol=symbol,
        timestamp=timestamp,
        entry_time=timestamp,
        exit_time=timestamp + timedelta(minutes=5),
        size=size,
        direction="long",
        entry_price=Decimal("1.1000"),
        exit_price=Decimal("1.1010"),
        stop_loss=Decimal("1.0990"),
        take_profit=Decimal("1.1020")
    )


class TestClusteringDetector:
    """Test suite for ClusteringDetector"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.detector = ClusteringDetector()
        self.base_time = datetime(2025, 1, 15, 10, 0, 0)
    
    def test_initialization(self):
        """Test detector initialization"""
        # Default initialization
        detector = ClusteringDetector()
        assert detector.thresholds is not None
        assert detector.thresholds.temporal_window == timedelta(minutes=5)
        assert detector.thresholds.max_trades_per_window == 3
        
        # Custom thresholds
        custom_thresholds = ClusteringThresholds(
            temporal_window=timedelta(minutes=10),
            max_trades_per_window=5
        )
        detector = ClusteringDetector(custom_thresholds)
        assert detector.thresholds.temporal_window == timedelta(minutes=10)
        assert detector.thresholds.max_trades_per_window == 5
    
    def test_find_temporal_clusters_no_clustering(self):
        """Test temporal clustering with well-spaced trades"""
        trades = [
            create_test_trade("T1", timestamp=self.base_time),
            create_test_trade("T2", timestamp=self.base_time + timedelta(minutes=10)),
            create_test_trade("T3", timestamp=self.base_time + timedelta(minutes=20)),
        ]
        
        clusters = self.detector.find_temporal_clusters(trades)
        assert len(clusters) == 0  # No clustering detected
    
    def test_find_temporal_clusters_with_clustering(self):
        """Test temporal clustering detection with clustered trades"""
        # Create 5 trades within 2 minutes (exceeds threshold of 3 per 5 minutes)
        trades = [
            create_test_trade("T1", timestamp=self.base_time),
            create_test_trade("T2", timestamp=self.base_time + timedelta(seconds=30)),
            create_test_trade("T3", timestamp=self.base_time + timedelta(minutes=1)),
            create_test_trade("T4", timestamp=self.base_time + timedelta(seconds=90)),
            create_test_trade("T5", timestamp=self.base_time + timedelta(minutes=2)),
        ]
        
        clusters = self.detector.find_temporal_clusters(trades)
        assert len(clusters) > 0
        
        cluster = clusters[0]
        assert cluster.trade_count == 5
        assert cluster.cluster_score > 0.5  # High density should give high score
    
    def test_find_symbol_clusters(self):
        """Test symbol-based clustering detection"""
        # Create trades concentrated on one symbol
        trades = [
            create_test_trade("T1", symbol="EURUSD", timestamp=self.base_time),
            create_test_trade("T2", symbol="EURUSD", timestamp=self.base_time + timedelta(minutes=1)),
            create_test_trade("T3", symbol="EURUSD", timestamp=self.base_time + timedelta(minutes=2)),
            create_test_trade("T4", symbol="EURUSD", timestamp=self.base_time + timedelta(minutes=3)),
            create_test_trade("T5", symbol="EURUSD", timestamp=self.base_time + timedelta(minutes=4)),
            create_test_trade("T6", symbol="EURUSD", timestamp=self.base_time + timedelta(minutes=5)),
            create_test_trade("T7", symbol="GBPUSD", timestamp=self.base_time + timedelta(minutes=6)),
        ]
        
        clusters = self.detector.find_symbol_clusters(trades)
        assert len(clusters) > 0
        
        # Should detect EURUSD concentration
        eurusd_cluster = next((c for c in clusters if c.symbol == "EURUSD"), None)
        assert eurusd_cluster is not None
        assert eurusd_cluster.trade_count >= 6
    
    def test_detect_synchronization(self):
        """Test cross-account synchronization detection"""
        # Create synchronized trades across multiple accounts
        trades = [
            create_test_trade("T1", account_id="ACC001", timestamp=self.base_time),
            create_test_trade("T2", account_id="ACC002", timestamp=self.base_time + timedelta(seconds=10)),
            create_test_trade("T3", account_id="ACC003", timestamp=self.base_time + timedelta(seconds=15)),
            # Another sync event
            create_test_trade("T4", account_id="ACC001", timestamp=self.base_time + timedelta(minutes=5)),
            create_test_trade("T5", account_id="ACC002", timestamp=self.base_time + timedelta(minutes=5, seconds=5)),
        ]
        
        sync_events = self.detector.detect_synchronization(trades)
        assert len(sync_events) > 0
        
        # First sync event should have 3 accounts
        first_event = sync_events[0]
        assert len(first_event.accounts) >= 2
        assert first_event.sync_score > 0
    
    def test_calculate_clustering_risk(self):
        """Test overall risk score calculation"""
        # Create various clustering patterns
        temporal_clusters = [
            TemporalCluster(
                start_time=self.base_time,
                end_time=self.base_time + timedelta(minutes=2),
                trades=[create_test_trade(f"T{i}") for i in range(5)],
                window_size=timedelta(minutes=5),
                cluster_score=0.8
            )
        ]
        
        symbol_clusters = [
            SymbolCluster(
                symbol="EURUSD",
                trades=[create_test_trade(f"T{i}") for i in range(6)],
                time_window=timedelta(minutes=10),
                concentration_score=0.7
            )
        ]
        
        sync_events = [
            SynchronizationEvent(
                timestamp=self.base_time,
                accounts=["ACC001", "ACC002", "ACC003"],
                trades=[create_test_trade(f"T{i}") for i in range(3)],
                synchronization_window=timedelta(seconds=30),
                sync_score=0.9
            )
        ]
        
        risk_score = self.detector.calculate_clustering_risk(
            temporal_clusters, symbol_clusters, sync_events
        )
        
        assert 0 <= risk_score <= 1
        assert risk_score > 0.5  # Should be high risk with these patterns
    
    def test_complete_analysis(self):
        """Test complete clustering analysis workflow"""
        # Create a mix of normal and suspicious trades
        trades = []
        
        # Normal trades
        for i in range(3):
            trades.append(
                create_test_trade(
                    f"N{i}",
                    account_id="ACC001",
                    timestamp=self.base_time + timedelta(minutes=i*15)
                )
            )
        
        # Clustered trades
        cluster_time = self.base_time + timedelta(hours=1)
        for i in range(5):
            trades.append(
                create_test_trade(
                    f"C{i}",
                    account_id="ACC001",
                    timestamp=cluster_time + timedelta(seconds=i*20)
                )
            )
        
        # Synchronized trades
        sync_time = self.base_time + timedelta(hours=2)
        for i, acc in enumerate(["ACC001", "ACC002", "ACC003"]):
            trades.append(
                create_test_trade(
                    f"S{i}",
                    account_id=acc,
                    timestamp=sync_time + timedelta(seconds=i*5)
                )
            )
        
        analysis = self.detector.analyze_clustering(trades)
        
        assert isinstance(analysis, ClusteringAnalysis)
        assert len(analysis.temporal_clusters) > 0
        assert len(analysis.synchronization_events) > 0
        assert analysis.risk_score > 0
        assert len(analysis.suspicious_patterns) > 0
        assert len(analysis.recommendations) > 0
    
    def test_empty_trades(self):
        """Test handling of empty trade list"""
        analysis = self.detector.analyze_clustering([])
        
        assert analysis.risk_score == 0.0
        assert len(analysis.temporal_clusters) == 0
        assert len(analysis.symbol_clusters) == 0
        assert len(analysis.synchronization_events) == 0
    
    def test_analysis_window_filtering(self):
        """Test filtering trades by analysis window"""
        trades = [
            create_test_trade("T1", timestamp=self.base_time - timedelta(hours=2)),
            create_test_trade("T2", timestamp=self.base_time - timedelta(hours=1)),
            create_test_trade("T3", timestamp=self.base_time),
        ]
        
        # Analyze only last hour
        analysis = self.detector.analyze_clustering(
            trades, 
            analysis_window=timedelta(hours=1)
        )
        
        # Should only analyze T2 and T3
        all_trade_ids = set()
        for cluster in analysis.temporal_clusters:
            all_trade_ids.update(t.id for t in cluster.trades)
        
        assert "T1" not in all_trade_ids
    
    def test_recommendations_generation(self):
        """Test that recommendations are generated based on risk level"""
        detector = ClusteringDetector()
        
        # Test critical risk recommendations
        critical_patterns = ["High-density temporal clustering detected: 5 clusters"]
        critical_recs = detector._generate_recommendations(0.9, critical_patterns)
        assert any("CRITICAL" in r for r in critical_recs)
        
        # Test high risk recommendations
        high_recs = detector._generate_recommendations(0.75, [])
        assert any("HIGH RISK" in r for r in high_recs)
        
        # Test medium risk recommendations
        medium_recs = detector._generate_recommendations(0.55, [])
        assert any("MEDIUM RISK" in r for r in medium_recs)
        
        # Test low risk recommendations
        low_recs = detector._generate_recommendations(0.35, [])
        assert any("LOW RISK" in r for r in low_recs)
    
    def test_suspicious_pattern_identification(self):
        """Test identification of specific suspicious patterns"""
        # Create patterns for testing
        temporal_clusters = [
            TemporalCluster(
                start_time=self.base_time,
                end_time=self.base_time + timedelta(minutes=1),
                trades=[create_test_trade(f"T{i}") for i in range(10)],
                window_size=timedelta(minutes=5),
                cluster_score=0.9
            )
        ]
        
        symbol_clusters = [
            SymbolCluster(
                symbol="EURUSD",
                trades=[create_test_trade(f"T{i}") for i in range(10)],
                time_window=timedelta(minutes=10),
                concentration_score=0.85
            )
        ]
        
        # Create regular interval sync events
        sync_events = []
        for i in range(10):
            sync_events.append(
                SynchronizationEvent(
                    timestamp=self.base_time + timedelta(minutes=i*5),  # Regular 5-minute intervals
                    accounts=["ACC001", "ACC002"],
                    trades=[create_test_trade(f"S{i}_{j}") for j in range(2)],
                    synchronization_window=timedelta(seconds=30),
                    sync_score=0.7
                )
            )
        
        patterns = self.detector._identify_suspicious_patterns(
            temporal_clusters, symbol_clusters, sync_events
        )
        
        assert len(patterns) > 0
        assert any("High-density temporal clustering" in p for p in patterns)
        assert any("Excessive symbol concentration" in p for p in patterns)
        assert any("Cross-account synchronization" in p for p in patterns)
        assert any("Regular synchronization intervals" in p for p in patterns)