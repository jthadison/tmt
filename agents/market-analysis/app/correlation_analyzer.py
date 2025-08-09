"""
Correlation Analysis Engine - Advanced correlation tracking and anomaly detection
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
from decimal import Decimal
import logging
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class CorrelationAnomaly:
    """Correlation anomaly representation"""
    pair1: str
    pair2: str
    current_correlation: float
    historical_correlation: float
    deviation: float
    severity: str  # low, moderate, high, extreme
    timestamp: datetime


class CorrelationAnalyzer:
    """Advanced correlation tracking and analysis for forex pairs and indices"""
    
    def __init__(self):
        self.major_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
            'AUDUSD', 'USDCAD', 'NZDUSD'
        ]
        
        self.minor_pairs = [
            'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY',
            'EURGBP', 'EURAUD', 'EURNZD', 'EURCAD'
        ]
        
        self.indices = ['DXY', 'US30', 'NAS100', 'SPX500', 'VIX']
        
        self.correlation_periods = [20, 50, 200]  # Different timeframes
        
        # Historical correlation storage
        self.historical_correlations: Dict[str, deque] = {}
        self.max_history_size = 1000
        
        # Known correlation relationships
        self.expected_correlations = {
            ('EURUSD', 'DXY'): -0.85,  # Strong negative
            ('EURUSD', 'GBPUSD'): 0.75,  # Positive
            ('EURUSD', 'USDCHF'): -0.95,  # Strong negative
            ('AUDUSD', 'NZDUSD'): 0.85,  # Strong positive
            ('USDJPY', 'US30'): 0.60,  # Moderate positive
            ('SPX500', 'VIX'): -0.75,  # Negative (risk on/off)
        }
    
    def calculate_correlation_matrix(
        self, 
        price_data_dict: Dict[str, List[Dict]], 
        period: int = 50
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix for all tracked instruments
        
        Args:
            price_data_dict: Dictionary of instrument price data
            period: Period for correlation calculation
            
        Returns:
            Correlation matrix
        """
        if not price_data_dict:
            return {}
        
        # Prepare price series
        instruments = list(price_data_dict.keys())
        price_changes = {}
        
        for instrument in instruments:
            if len(price_data_dict[instrument]) < period + 1:
                logger.warning(f"Insufficient data for {instrument}, skipping")
                continue
            
            prices = [float(candle['close']) for candle in price_data_dict[instrument]]
            
            # Calculate log returns
            if len(prices) > period:
                log_returns = [np.log(prices[i] / prices[i-1]) 
                             for i in range(1, len(prices))]
                price_changes[instrument] = log_returns[-period:]
            else:
                price_changes[instrument] = []
        
        # Calculate correlation matrix
        correlation_matrix = {}
        
        for inst1 in price_changes:
            correlation_matrix[inst1] = {}
            
            for inst2 in price_changes:
                if len(price_changes[inst1]) == 0 or len(price_changes[inst2]) == 0:
                    correlation_matrix[inst1][inst2] = 0.0
                elif inst1 == inst2:
                    correlation_matrix[inst1][inst2] = 1.0
                else:
                    try:
                        corr = np.corrcoef(
                            price_changes[inst1], 
                            price_changes[inst2]
                        )[0, 1]
                        
                        # Handle NaN values
                        if np.isnan(corr):
                            corr = 0.0
                        
                        correlation_matrix[inst1][inst2] = round(corr, 4)
                    except Exception as e:
                        logger.error(f"Error calculating correlation for {inst1}/{inst2}: {e}")
                        correlation_matrix[inst1][inst2] = 0.0
        
        return correlation_matrix
    
    def calculate_rolling_correlations(
        self, 
        price_data_dict: Dict[str, List[Dict]]
    ) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Calculate correlations across multiple timeframes
        
        Args:
            price_data_dict: Dictionary of instrument price data
            
        Returns:
            Correlations for each period
        """
        rolling_correlations = {}
        
        for period in self.correlation_periods:
            rolling_correlations[period] = self.calculate_correlation_matrix(
                price_data_dict, 
                period
            )
        
        return rolling_correlations
    
    def detect_correlation_anomalies(
        self, 
        current_correlations: Dict[str, Dict[str, float]],
        threshold: float = 0.3
    ) -> List[CorrelationAnomaly]:
        """
        Detect unusual correlation patterns that might indicate market stress
        
        Args:
            current_correlations: Current correlation matrix
            threshold: Deviation threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        current_time = datetime.now(timezone.utc)
        
        for pair1 in current_correlations:
            for pair2 in current_correlations[pair1]:
                if pair1 >= pair2:  # Avoid duplicates and self-correlation
                    continue
                
                current_corr = current_correlations[pair1][pair2]
                
                # Get expected correlation
                expected_corr = self._get_expected_correlation(pair1, pair2)
                
                if expected_corr is not None:
                    deviation = abs(current_corr - expected_corr)
                    
                    if deviation > threshold:
                        severity = self._assess_anomaly_severity(deviation)
                        
                        anomalies.append(CorrelationAnomaly(
                            pair1=pair1,
                            pair2=pair2,
                            current_correlation=current_corr,
                            historical_correlation=expected_corr,
                            deviation=deviation,
                            severity=severity,
                            timestamp=current_time
                        ))
        
        return sorted(anomalies, key=lambda x: x.deviation, reverse=True)
    
    def analyze_correlation_breakdown(
        self, 
        anomalies: List[CorrelationAnomaly]
    ) -> Dict[str, Any]:
        """
        Analyze correlation breakdowns for market regime identification
        
        Args:
            anomalies: List of correlation anomalies
            
        Returns:
            Breakdown analysis
        """
        if not anomalies:
            return {
                'breakdown_detected': False,
                'severity': 'none',
                'affected_instruments': [],
                'market_implication': 'Normal correlations'
            }
        
        # Count severe anomalies
        severe_count = sum(1 for a in anomalies if a.severity in ['high', 'extreme'])
        moderate_count = sum(1 for a in anomalies if a.severity == 'moderate')
        
        # Get affected instruments
        affected_instruments = set()
        for anomaly in anomalies:
            affected_instruments.add(anomaly.pair1)
            affected_instruments.add(anomaly.pair2)
        
        # Determine overall severity
        if severe_count >= 3:
            overall_severity = 'extreme'
            market_implication = 'Major correlation breakdown - possible market stress or regime change'
        elif severe_count >= 1:
            overall_severity = 'high'
            market_implication = 'Significant correlation changes - increased uncertainty'
        elif moderate_count >= 3:
            overall_severity = 'moderate'
            market_implication = 'Multiple correlation shifts - monitor closely'
        else:
            overall_severity = 'low'
            market_implication = 'Minor correlation variations within normal range'
        
        return {
            'breakdown_detected': severe_count > 0,
            'severity': overall_severity,
            'affected_instruments': list(affected_instruments),
            'anomaly_count': {
                'extreme': sum(1 for a in anomalies if a.severity == 'extreme'),
                'high': sum(1 for a in anomalies if a.severity == 'high'),
                'moderate': moderate_count,
                'low': sum(1 for a in anomalies if a.severity == 'low')
            },
            'market_implication': market_implication,
            'top_anomalies': anomalies[:5] if anomalies else []
        }
    
    def calculate_correlation_stability(
        self, 
        instrument: str,
        correlation_history: Dict[str, List[float]]
    ) -> Dict[str, float]:
        """
        Calculate correlation stability metrics for an instrument
        
        Args:
            instrument: Instrument to analyze
            correlation_history: Historical correlations with other instruments
            
        Returns:
            Stability metrics
        """
        stability_metrics = {}
        
        for other_instrument, correlations in correlation_history.items():
            if len(correlations) < 20:
                stability_metrics[other_instrument] = 1.0  # Not enough data
                continue
            
            # Calculate standard deviation of correlations
            std_dev = np.std(correlations)
            
            # Calculate stability score (lower std dev = higher stability)
            stability_score = max(0, 1 - (std_dev * 2))  # Scale std dev to 0-1
            
            stability_metrics[other_instrument] = round(stability_score, 3)
        
        return stability_metrics
    
    def identify_correlation_clusters(
        self, 
        correlation_matrix: Dict[str, Dict[str, float]],
        threshold: float = 0.7
    ) -> List[List[str]]:
        """
        Identify clusters of highly correlated instruments
        
        Args:
            correlation_matrix: Correlation matrix
            threshold: Correlation threshold for clustering
            
        Returns:
            List of instrument clusters
        """
        clusters = []
        processed = set()
        
        for inst1 in correlation_matrix:
            if inst1 in processed:
                continue
            
            cluster = [inst1]
            processed.add(inst1)
            
            for inst2 in correlation_matrix[inst1]:
                if inst2 == inst1 or inst2 in processed:
                    continue
                
                # Check if inst2 is highly correlated with all cluster members
                is_correlated = True
                for cluster_member in cluster:
                    corr = abs(correlation_matrix[cluster_member].get(inst2, 0))
                    if corr < threshold:
                        is_correlated = False
                        break
                
                if is_correlated:
                    cluster.append(inst2)
                    processed.add(inst2)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def calculate_diversification_score(
        self, 
        portfolio: List[str],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """
        Calculate portfolio diversification score based on correlations
        
        Args:
            portfolio: List of instruments in portfolio
            correlation_matrix: Correlation matrix
            
        Returns:
            Diversification score (0-100)
        """
        if len(portfolio) < 2:
            return 0.0
        
        correlations = []
        
        for i, inst1 in enumerate(portfolio):
            for j, inst2 in enumerate(portfolio):
                if i < j and inst1 in correlation_matrix and inst2 in correlation_matrix[inst1]:
                    correlations.append(abs(correlation_matrix[inst1][inst2]))
        
        if not correlations:
            return 50.0  # Default if no correlation data
        
        # Average absolute correlation
        avg_correlation = np.mean(correlations)
        
        # Convert to diversification score (lower correlation = higher diversification)
        diversification_score = (1 - avg_correlation) * 100
        
        return round(diversification_score, 2)
    
    def _get_expected_correlation(self, inst1: str, inst2: str) -> Optional[float]:
        """
        Get expected correlation between two instruments
        
        Args:
            inst1: First instrument
            inst2: Second instrument
            
        Returns:
            Expected correlation or None
        """
        # Check known relationships
        if (inst1, inst2) in self.expected_correlations:
            return self.expected_correlations[(inst1, inst2)]
        elif (inst2, inst1) in self.expected_correlations:
            return self.expected_correlations[(inst2, inst1)]
        
        # Check historical average if available
        history_key = f"{inst1}_{inst2}"
        if history_key in self.historical_correlations:
            history = list(self.historical_correlations[history_key])
            if len(history) >= 20:
                return np.mean(history)
        
        return None
    
    def _assess_anomaly_severity(self, deviation: float) -> str:
        """
        Assess severity of correlation anomaly
        
        Args:
            deviation: Correlation deviation
            
        Returns:
            Severity level
        """
        if deviation > 0.6:
            return 'extreme'
        elif deviation > 0.4:
            return 'high'
        elif deviation > 0.25:
            return 'moderate'
        else:
            return 'low'
    
    def update_correlation_history(
        self, 
        correlation_matrix: Dict[str, Dict[str, float]]
    ):
        """
        Update historical correlation records
        
        Args:
            correlation_matrix: Current correlation matrix
        """
        for inst1 in correlation_matrix:
            for inst2 in correlation_matrix[inst1]:
                if inst1 >= inst2:  # Avoid duplicates
                    continue
                
                history_key = f"{inst1}_{inst2}"
                
                if history_key not in self.historical_correlations:
                    self.historical_correlations[history_key] = deque(
                        maxlen=self.max_history_size
                    )
                
                self.historical_correlations[history_key].append(
                    correlation_matrix[inst1][inst2]
                )