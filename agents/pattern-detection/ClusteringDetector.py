"""
Trade clustering detection system for identifying suspicious patterns
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade for analysis"""
    id: str
    account_id: str
    symbol: str
    timestamp: datetime
    entry_time: datetime
    exit_time: Optional[datetime]
    size: Decimal
    direction: str  # 'long' or 'short'
    entry_price: Decimal
    exit_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]


@dataclass
class TemporalCluster:
    """Represents a temporal cluster of trades"""
    start_time: datetime
    end_time: datetime
    trades: List[Trade]
    window_size: timedelta
    cluster_score: float
    
    @property
    def trade_count(self) -> int:
        return len(self.trades)
    
    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time


@dataclass
class SymbolCluster:
    """Represents clustering of trades on the same symbol"""
    symbol: str
    trades: List[Trade]
    time_window: timedelta
    concentration_score: float
    
    @property
    def trade_count(self) -> int:
        return len(self.trades)


@dataclass
class SynchronizationEvent:
    """Represents synchronized trading across accounts"""
    timestamp: datetime
    accounts: List[str]
    trades: List[Trade]
    synchronization_window: timedelta
    sync_score: float


@dataclass
class ClusteringAnalysis:
    """Complete clustering analysis results"""
    temporal_clusters: List[TemporalCluster]
    symbol_clusters: List[SymbolCluster]
    synchronization_events: List[SynchronizationEvent]
    risk_score: float
    suspicious_patterns: List[str]
    recommendations: List[str]


@dataclass
class ClusteringThresholds:
    """Configuration thresholds for clustering detection"""
    temporal_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_trades_per_window: int = 3
    symbol_window: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    max_symbol_trades: int = 5
    cross_account_window: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    synchronization_threshold: int = 2  # Min accounts for sync detection
    
    # Risk scoring thresholds
    low_risk_threshold: float = 0.3
    medium_risk_threshold: float = 0.5
    high_risk_threshold: float = 0.7
    critical_risk_threshold: float = 0.85


class ClusteringDetector:
    """Detects clustering patterns in trading data"""
    
    def __init__(self, thresholds: Optional[ClusteringThresholds] = None):
        self.thresholds = thresholds or ClusteringThresholds()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_clustering(
        self, 
        trades: List[Trade], 
        analysis_window: Optional[timedelta] = None
    ) -> ClusteringAnalysis:
        """
        Perform complete clustering analysis on trading data
        """
        if analysis_window:
            trades = self._filter_trades_by_window(trades, analysis_window)
        
        # Sort trades by timestamp for temporal analysis
        trades.sort(key=lambda t: t.timestamp)
        
        # Perform different clustering analyses
        temporal_clusters = self.find_temporal_clusters(trades)
        symbol_clusters = self.find_symbol_clusters(trades)
        sync_events = self.detect_synchronization(trades)
        
        # Calculate overall risk score
        risk_score = self.calculate_clustering_risk(
            temporal_clusters, 
            symbol_clusters, 
            sync_events
        )
        
        # Generate suspicious patterns and recommendations
        suspicious_patterns = self._identify_suspicious_patterns(
            temporal_clusters, symbol_clusters, sync_events
        )
        recommendations = self._generate_recommendations(
            risk_score, suspicious_patterns
        )
        
        return ClusteringAnalysis(
            temporal_clusters=temporal_clusters,
            symbol_clusters=symbol_clusters,
            synchronization_events=sync_events,
            risk_score=risk_score,
            suspicious_patterns=suspicious_patterns,
            recommendations=recommendations
        )
    
    def find_temporal_clusters(self, trades: List[Trade]) -> List[TemporalCluster]:
        """
        Detect temporal clustering of trades within time windows
        """
        if not trades:
            return []
        
        clusters = []
        window_size = self.thresholds.temporal_window
        
        # Sliding window approach
        for i, start_trade in enumerate(trades):
            window_end = start_trade.timestamp + window_size
            window_trades = []
            
            # Collect trades within the window
            for trade in trades[i:]:
                if trade.timestamp <= window_end:
                    window_trades.append(trade)
                else:
                    break
            
            # Check if window exceeds threshold
            if len(window_trades) > self.thresholds.max_trades_per_window:
                # Calculate clustering score based on trade density
                duration = (window_trades[-1].timestamp - window_trades[0].timestamp).total_seconds()
                if duration > 0:
                    density = len(window_trades) / (duration / 60)  # trades per minute
                else:
                    density = float('inf')
                
                cluster_score = min(1.0, density / 2.0)  # Normalize to 0-1
                
                cluster = TemporalCluster(
                    start_time=window_trades[0].timestamp,
                    end_time=window_trades[-1].timestamp,
                    trades=window_trades,
                    window_size=window_size,
                    cluster_score=cluster_score
                )
                
                # Avoid duplicate overlapping clusters
                if not self._is_duplicate_cluster(cluster, clusters):
                    clusters.append(cluster)
        
        return clusters
    
    def find_symbol_clusters(self, trades: List[Trade]) -> List[SymbolCluster]:
        """
        Detect clustering of trades on the same symbols
        """
        symbol_groups = defaultdict(list)
        
        # Group trades by symbol
        for trade in trades:
            symbol_groups[trade.symbol].append(trade)
        
        clusters = []
        
        for symbol, symbol_trades in symbol_groups.items():
            # Sort by timestamp
            symbol_trades.sort(key=lambda t: t.timestamp)
            
            # Check for temporal concentration within symbol
            for i in range(len(symbol_trades)):
                window_end = symbol_trades[i].timestamp + self.thresholds.symbol_window
                window_trades = []
                
                for trade in symbol_trades[i:]:
                    if trade.timestamp <= window_end:
                        window_trades.append(trade)
                    else:
                        break
                
                if len(window_trades) > self.thresholds.max_symbol_trades:
                    # Calculate concentration score
                    time_spread = (window_trades[-1].timestamp - window_trades[0].timestamp).total_seconds()
                    if time_spread > 0:
                        concentration = len(window_trades) / (time_spread / 60)
                    else:
                        concentration = float('inf')
                    
                    concentration_score = min(1.0, concentration / 3.0)
                    
                    cluster = SymbolCluster(
                        symbol=symbol,
                        trades=window_trades,
                        time_window=self.thresholds.symbol_window,
                        concentration_score=concentration_score
                    )
                    
                    if not self._is_duplicate_symbol_cluster(cluster, clusters):
                        clusters.append(cluster)
        
        return clusters
    
    def detect_synchronization(self, trades: List[Trade]) -> List[SynchronizationEvent]:
        """
        Detect synchronized trading across multiple accounts
        """
        sync_events = []
        
        # Group trades by timestamp windows
        time_buckets = defaultdict(list)
        
        for trade in trades:
            # Round to sync window
            bucket_time = self._round_to_window(
                trade.timestamp, 
                self.thresholds.cross_account_window
            )
            time_buckets[bucket_time].append(trade)
        
        # Check each bucket for cross-account synchronization
        for bucket_time, bucket_trades in time_buckets.items():
            # Group by account
            account_trades = defaultdict(list)
            for trade in bucket_trades:
                account_trades[trade.account_id].append(trade)
            
            # Check if multiple accounts traded in this window
            if len(account_trades) >= self.thresholds.synchronization_threshold:
                # Calculate synchronization score
                total_trades = len(bucket_trades)
                num_accounts = len(account_trades)
                
                # Higher score for more accounts and more synchronized trades
                sync_score = min(1.0, (num_accounts - 1) / 3.0 * (total_trades / num_accounts) / 2.0)
                
                event = SynchronizationEvent(
                    timestamp=bucket_time,
                    accounts=list(account_trades.keys()),
                    trades=bucket_trades,
                    synchronization_window=self.thresholds.cross_account_window,
                    sync_score=sync_score
                )
                
                sync_events.append(event)
        
        return sync_events
    
    def calculate_clustering_risk(
        self,
        temporal_clusters: List[TemporalCluster],
        symbol_clusters: List[SymbolCluster],
        sync_events: List[SynchronizationEvent]
    ) -> float:
        """
        Calculate overall clustering risk score (0-1)
        """
        risk_components = []
        
        # Temporal clustering risk
        if temporal_clusters:
            temporal_risk = np.mean([c.cluster_score for c in temporal_clusters])
            risk_components.append(temporal_risk * 0.3)  # 30% weight
        
        # Symbol clustering risk
        if symbol_clusters:
            symbol_risk = np.mean([c.concentration_score for c in symbol_clusters])
            risk_components.append(symbol_risk * 0.3)  # 30% weight
        
        # Synchronization risk
        if sync_events:
            sync_risk = np.mean([e.sync_score for e in sync_events])
            risk_components.append(sync_risk * 0.4)  # 40% weight - highest concern
        
        # Calculate weighted average
        if risk_components:
            return min(1.0, sum(risk_components))
        
        return 0.0
    
    def _filter_trades_by_window(
        self, 
        trades: List[Trade], 
        window: timedelta
    ) -> List[Trade]:
        """Filter trades to analysis window"""
        if not trades:
            return []
        
        latest_time = max(t.timestamp for t in trades)
        cutoff_time = latest_time - window
        
        return [t for t in trades if t.timestamp >= cutoff_time]
    
    def _round_to_window(self, timestamp: datetime, window: timedelta) -> datetime:
        """Round timestamp to nearest window boundary"""
        window_seconds = window.total_seconds()
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        rounded_seconds = (seconds_since_epoch // window_seconds) * window_seconds
        return epoch + timedelta(seconds=rounded_seconds)
    
    def _is_duplicate_cluster(
        self, 
        new_cluster: TemporalCluster, 
        existing_clusters: List[TemporalCluster]
    ) -> bool:
        """Check if cluster significantly overlaps with existing clusters"""
        for existing in existing_clusters:
            # Check time overlap
            overlap_start = max(new_cluster.start_time, existing.start_time)
            overlap_end = min(new_cluster.end_time, existing.end_time)
            
            if overlap_start < overlap_end:
                # Calculate trade overlap
                new_trade_ids = {t.id for t in new_cluster.trades}
                existing_trade_ids = {t.id for t in existing.trades}
                overlap_ratio = len(new_trade_ids & existing_trade_ids) / len(new_trade_ids)
                
                if overlap_ratio > 0.7:  # 70% overlap threshold
                    return True
        
        return False
    
    def _is_duplicate_symbol_cluster(
        self,
        new_cluster: SymbolCluster,
        existing_clusters: List[SymbolCluster]
    ) -> bool:
        """Check if symbol cluster overlaps with existing clusters"""
        for existing in existing_clusters:
            if existing.symbol != new_cluster.symbol:
                continue
                
            # Check trade overlap
            new_trade_ids = {t.id for t in new_cluster.trades}
            existing_trade_ids = {t.id for t in existing.trades}
            overlap_ratio = len(new_trade_ids & existing_trade_ids) / len(new_trade_ids)
            
            if overlap_ratio > 0.7:
                return True
        
        return False
    
    def _identify_suspicious_patterns(
        self,
        temporal_clusters: List[TemporalCluster],
        symbol_clusters: List[SymbolCluster],
        sync_events: List[SynchronizationEvent]
    ) -> List[str]:
        """Identify specific suspicious patterns"""
        patterns = []
        
        # Check temporal clustering patterns
        if temporal_clusters:
            high_density_clusters = [c for c in temporal_clusters if c.cluster_score > 0.7]
            if high_density_clusters:
                patterns.append(
                    f"High-density temporal clustering detected: {len(high_density_clusters)} clusters"
                )
        
        # Check symbol concentration
        if symbol_clusters:
            high_concentration = [c for c in symbol_clusters if c.concentration_score > 0.7]
            if high_concentration:
                symbols = list(set(c.symbol for c in high_concentration))
                patterns.append(
                    f"Excessive symbol concentration on: {', '.join(symbols[:3])}"
                )
        
        # Check synchronization patterns
        if sync_events:
            high_sync = [e for e in sync_events if e.sync_score > 0.6]
            if high_sync:
                patterns.append(
                    f"Cross-account synchronization detected: {len(high_sync)} events"
                )
            
            # Check for regular synchronization intervals
            if len(sync_events) > 5:
                intervals = []
                for i in range(1, len(sync_events)):
                    interval = (sync_events[i].timestamp - sync_events[i-1].timestamp).total_seconds()
                    intervals.append(interval)
                
                if intervals:
                    cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
                    if cv < 0.3:  # Low coefficient of variation indicates regularity
                        patterns.append("Regular synchronization intervals detected")
        
        return patterns
    
    def _generate_recommendations(
        self,
        risk_score: float,
        suspicious_patterns: List[str]
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if risk_score > self.thresholds.critical_risk_threshold:
            recommendations.append("CRITICAL: Immediate action required - pause trading and adjust parameters")
            recommendations.append("Increase minimum time between trades to at least 2 minutes")
            recommendations.append("Add random delays (30-120 seconds) between account operations")
        elif risk_score > self.thresholds.high_risk_threshold:
            recommendations.append("HIGH RISK: Adjust trading patterns within 24 hours")
            recommendations.append("Introduce 15-60 second random delays between trades")
            recommendations.append("Reduce correlation between accounts by varying trade timing")
        elif risk_score > self.thresholds.medium_risk_threshold:
            recommendations.append("MEDIUM RISK: Monitor closely and prepare adjustments")
            recommendations.append("Consider adding 5-30 second delays between similar trades")
            recommendations.append("Vary position sizes more to reduce precision patterns")
        elif risk_score > self.thresholds.low_risk_threshold:
            recommendations.append("LOW RISK: Continue monitoring, minor adjustments recommended")
            recommendations.append("Maintain current variance levels")
        
        # Pattern-specific recommendations
        if "High-density temporal clustering" in str(suspicious_patterns):
            recommendations.append("Spread trades over longer time periods")
        
        if "Excessive symbol concentration" in str(suspicious_patterns):
            recommendations.append("Diversify trading across more symbols")
        
        if "Cross-account synchronization" in str(suspicious_patterns):
            recommendations.append("Desynchronize account operations with random delays")
        
        if "Regular synchronization intervals" in str(suspicious_patterns):
            recommendations.append("Randomize timing patterns to break regularity")
        
        return recommendations