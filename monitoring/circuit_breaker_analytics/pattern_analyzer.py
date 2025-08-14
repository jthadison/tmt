"""
Circuit Breaker Pattern Analysis and Failure Prediction for TMT Trading System

Analyzes circuit breaker activation patterns to:
1. Predict potential failures before they occur
2. Identify systemic issues causing frequent circuit breaker trips
3. Optimize circuit breaker thresholds
4. Generate insights for system reliability improvements
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FailureCategory(Enum):
    """Categories of circuit breaker failures"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RISK_THRESHOLD_BREACH = "risk_threshold_breach"
    CONNECTIVITY_ISSUE = "connectivity_issue"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    COMPLIANCE_VIOLATION = "compliance_violation"
    EXTERNAL_DEPENDENCY = "external_dependency"
    UNKNOWN = "unknown"


class PatternType(Enum):
    """Types of failure patterns detected"""
    CASCADING_FAILURE = "cascading_failure"
    PERIODIC_FAILURE = "periodic_failure"
    GRADUAL_DEGRADATION = "gradual_degradation"
    SUDDEN_SPIKE = "sudden_spike"
    CORRELATED_FAILURE = "correlated_failure"
    ISOLATED_INCIDENT = "isolated_incident"


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker activation event"""
    timestamp: datetime
    account_id: str
    agent_name: str
    trigger_reason: str
    failure_category: FailureCategory
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    recovery_time: Optional[timedelta]
    related_events: List[str]


@dataclass
class FailurePattern:
    """Detected failure pattern"""
    pattern_id: str
    pattern_type: PatternType
    frequency: int
    affected_accounts: List[str]
    affected_agents: List[str]
    common_triggers: List[str]
    time_pattern: Dict[str, Any]  # Hour, day of week patterns
    duration_stats: Dict[str, float]
    recovery_stats: Dict[str, float]
    severity_score: float
    prediction_confidence: float
    recommendations: List[str]


@dataclass
class PredictionResult:
    """Circuit breaker activation prediction"""
    account_id: str
    agent_name: str
    predicted_failure_time: datetime
    failure_probability: float
    predicted_category: FailureCategory
    confidence_score: float
    contributing_factors: List[str]
    preventive_actions: List[str]


class CircuitBreakerAnalytics:
    """
    Advanced analytics for circuit breaker monitoring and failure prediction.
    
    Features:
    - Historical pattern analysis
    - Failure prediction using ML
    - Root cause analysis
    - Threshold optimization
    - Failure clustering and correlation
    """
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.events_history: List[CircuitBreakerEvent] = []
        self.patterns: List[FailurePattern] = []
        self.prediction_model: Optional[RandomForestClassifier] = None
        self.scaler = StandardScaler()
        
        # Analysis configuration
        self.analysis_window = timedelta(days=30)  # Analyze last 30 days
        self.prediction_horizon = timedelta(hours=4)  # Predict next 4 hours
        self.pattern_min_frequency = 3  # Minimum occurrences to be a pattern
        self.clustering_eps = 0.5  # DBSCAN epsilon parameter
        
        # Circuit breaker metrics to monitor
        self.cb_metrics = {
            "activation_rate": "rate(tmt_circuit_breaker_activations_total[5m])",
            "recovery_time": "tmt_circuit_breaker_recovery_duration_seconds",
            "failure_reasons": "tmt_circuit_breaker_failure_reasons_total",
            "account_failures": "tmt_circuit_breaker_account_failures_total",
            "agent_failures": "tmt_circuit_breaker_agent_failures_total"
        }
        
        # Leading indicators for prediction
        self.leading_indicators = {
            "latency_p95": "histogram_quantile(0.95, rate(tmt_signal_execution_duration_seconds_bucket[5m]))",
            "error_rate": "rate(tmt_execution_errors_total[5m])",
            "memory_usage": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes",
            "cpu_usage": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "db_connections": "tmt_db_connections_active / tmt_db_connections_max",
            "message_queue_lag": "tmt_message_queue_lag_seconds",
            "api_response_time": "histogram_quantile(0.95, rate(tmt_api_response_duration_seconds_bucket[5m]))"
        }
    
    async def collect_circuit_breaker_events(self) -> List[CircuitBreakerEvent]:
        """Collect historical circuit breaker events from Prometheus"""
        logger.info("Collecting circuit breaker events...")
        
        end_time = datetime.utcnow()
        start_time = end_time - self.analysis_window
        
        events = []
        
        # Query circuit breaker activations
        activation_query = """
        increase(tmt_circuit_breaker_activations_total[1h])
        """
        
        activations = await self.query_prometheus_range(
            activation_query, start_time, end_time, "1h"
        )
        
        for series in activations:
            labels = series.get("metric", {})
            values = series.get("values", [])
            
            for timestamp, value in values:
                if float(value) > 0:  # Circuit breaker activated
                    # Collect related metrics
                    event_time = datetime.fromtimestamp(timestamp)
                    metrics_before, metrics_after = await self.collect_event_metrics(
                        labels.get("account_id", "unknown"),
                        labels.get("agent", "unknown"),
                        event_time
                    )
                    
                    event = CircuitBreakerEvent(
                        timestamp=event_time,
                        account_id=labels.get("account_id", "unknown"),
                        agent_name=labels.get("agent", "unknown"),
                        trigger_reason=labels.get("reason", "unknown"),
                        failure_category=self.categorize_failure(labels.get("reason", "unknown")),
                        metrics_before=metrics_before,
                        metrics_after=metrics_after,
                        recovery_time=await self.calculate_recovery_time(
                            labels.get("account_id", "unknown"),
                            event_time
                        ),
                        related_events=[]
                    )
                    
                    events.append(event)
        
        self.events_history = events
        logger.info(f"Collected {len(events)} circuit breaker events")
        return events
    
    async def analyze_failure_patterns(self) -> List[FailurePattern]:
        """Analyze patterns in circuit breaker failures"""
        logger.info("Analyzing failure patterns...")
        
        if not self.events_history:
            await self.collect_circuit_breaker_events()
        
        patterns = []
        
        # Group events by various dimensions for pattern detection
        patterns.extend(await self.detect_temporal_patterns())
        patterns.extend(await self.detect_account_patterns())
        patterns.extend(await self.detect_agent_patterns())
        patterns.extend(await self.detect_cascading_patterns())
        patterns.extend(await self.detect_metric_correlation_patterns())
        
        self.patterns = patterns
        logger.info(f"Detected {len(patterns)} failure patterns")
        return patterns
    
    async def detect_temporal_patterns(self) -> List[FailurePattern]:
        """Detect time-based failure patterns"""
        patterns = []
        
        # Convert events to DataFrame for easier analysis
        df = pd.DataFrame([{
            'timestamp': event.timestamp,
            'hour': event.timestamp.hour,
            'day_of_week': event.timestamp.weekday(),
            'account_id': event.account_id,
            'agent_name': event.agent_name,
            'trigger_reason': event.trigger_reason,
            'category': event.failure_category.value
        } for event in self.events_history])
        
        if df.empty:
            return patterns
        
        # Detect hourly patterns
        hourly_counts = df.groupby('hour').size()
        if hourly_counts.max() >= self.pattern_min_frequency:
            peak_hour = hourly_counts.idxmax()
            pattern = FailurePattern(
                pattern_id=f"hourly_peak_{peak_hour}",
                pattern_type=PatternType.PERIODIC_FAILURE,
                frequency=int(hourly_counts.max()),
                affected_accounts=df[df['hour'] == peak_hour]['account_id'].unique().tolist(),
                affected_agents=df[df['hour'] == peak_hour]['agent_name'].unique().tolist(),
                common_triggers=df[df['hour'] == peak_hour]['trigger_reason'].value_counts().head(3).index.tolist(),
                time_pattern={
                    'type': 'hourly',
                    'peak_hour': peak_hour,
                    'frequency_distribution': hourly_counts.to_dict()
                },
                duration_stats={},
                recovery_stats={},
                severity_score=self.calculate_severity_score(hourly_counts.max(), len(df)),
                prediction_confidence=0.8,
                recommendations=[
                    f"Investigate system load patterns around {peak_hour}:00",
                    "Consider pre-emptive scaling before peak hours",
                    "Review scheduled tasks and batch jobs"
                ]
            )
            patterns.append(pattern)
        
        # Detect weekly patterns
        weekly_counts = df.groupby('day_of_week').size()
        if weekly_counts.max() >= self.pattern_min_frequency:
            peak_day = weekly_counts.idxmax()
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            pattern = FailurePattern(
                pattern_id=f"weekly_peak_{day_names[peak_day]}",
                pattern_type=PatternType.PERIODIC_FAILURE,
                frequency=int(weekly_counts.max()),
                affected_accounts=df[df['day_of_week'] == peak_day]['account_id'].unique().tolist(),
                affected_agents=df[df['day_of_week'] == peak_day]['agent_name'].unique().tolist(),
                common_triggers=df[df['day_of_week'] == peak_day]['trigger_reason'].value_counts().head(3).index.tolist(),
                time_pattern={
                    'type': 'weekly',
                    'peak_day': day_names[peak_day],
                    'frequency_distribution': {day_names[i]: count for i, count in weekly_counts.items()}
                },
                duration_stats={},
                recovery_stats={},
                severity_score=self.calculate_severity_score(weekly_counts.max(), len(df)),
                prediction_confidence=0.7,
                recommendations=[
                    f"Investigate higher failure rates on {day_names[peak_day]}",
                    "Review market conditions and trading volume patterns",
                    "Consider different risk parameters for different days"
                ]
            )
            patterns.append(pattern)
        
        return patterns
    
    async def detect_cascading_patterns(self) -> List[FailurePattern]:
        """Detect cascading failure patterns"""
        patterns = []
        
        # Sort events by timestamp
        sorted_events = sorted(self.events_history, key=lambda x: x.timestamp)
        
        # Look for events that happen within short time windows
        cascade_window = timedelta(minutes=15)  # 15-minute window
        cascades = []
        
        i = 0
        while i < len(sorted_events):
            cascade_group = [sorted_events[i]]
            j = i + 1
            
            while j < len(sorted_events):
                if sorted_events[j].timestamp - sorted_events[i].timestamp <= cascade_window:
                    cascade_group.append(sorted_events[j])
                    j += 1
                else:
                    break
            
            if len(cascade_group) >= 3:  # At least 3 events in cascade
                cascades.append(cascade_group)
            
            i = j if j > i + 1 else i + 1
        
        for idx, cascade in enumerate(cascades):
            affected_accounts = list(set(event.account_id for event in cascade))
            affected_agents = list(set(event.agent_name for event in cascade))
            common_triggers = Counter(event.trigger_reason for event in cascade).most_common(3)
            
            pattern = FailurePattern(
                pattern_id=f"cascade_{idx}_{cascade[0].timestamp.strftime('%Y%m%d_%H%M')}",
                pattern_type=PatternType.CASCADING_FAILURE,
                frequency=len(cascade),
                affected_accounts=affected_accounts,
                affected_agents=affected_agents,
                common_triggers=[trigger for trigger, _ in common_triggers],
                time_pattern={
                    'type': 'cascade',
                    'start_time': cascade[0].timestamp.isoformat(),
                    'duration_minutes': (cascade[-1].timestamp - cascade[0].timestamp).total_seconds() / 60,
                    'event_sequence': [event.agent_name for event in cascade]
                },
                duration_stats={
                    'total_duration': (cascade[-1].timestamp - cascade[0].timestamp).total_seconds() / 60,
                    'events_count': len(cascade)
                },
                recovery_stats={},
                severity_score=self.calculate_severity_score(len(cascade), len(affected_accounts)),
                prediction_confidence=0.9,
                recommendations=[
                    "Investigate component dependencies and failure propagation",
                    "Consider circuit breaker isolation strategies",
                    "Review system architecture for single points of failure",
                    "Implement bulkhead pattern to prevent cascade failures"
                ]
            )
            patterns.append(pattern)
        
        return patterns
    
    async def detect_account_patterns(self) -> List[FailurePattern]:
        """Detect account-specific failure patterns"""
        patterns = []
        
        # Group by account
        account_failures = defaultdict(list)
        for event in self.events_history:
            account_failures[event.account_id].append(event)
        
        for account_id, events in account_failures.items():
            if len(events) >= self.pattern_min_frequency:
                # Analyze failure reasons for this account
                reasons = Counter(event.trigger_reason for event in events)
                categories = Counter(event.failure_category.value for event in events)
                
                pattern = FailurePattern(
                    pattern_id=f"account_{account_id}_pattern",
                    pattern_type=PatternType.CORRELATED_FAILURE,
                    frequency=len(events),
                    affected_accounts=[account_id],
                    affected_agents=list(set(event.agent_name for event in events)),
                    common_triggers=list(reasons.keys()),
                    time_pattern={
                        'type': 'account_specific',
                        'failure_frequency': len(events) / self.analysis_window.days,
                        'most_common_reason': reasons.most_common(1)[0][0],
                        'failure_distribution': dict(categories)
                    },
                    duration_stats={
                        'avg_recovery_time': np.mean([
                            event.recovery_time.total_seconds() / 60 
                            for event in events 
                            if event.recovery_time
                        ]) if any(event.recovery_time for event in events) else 0
                    },
                    recovery_stats={},
                    severity_score=self.calculate_severity_score(len(events), 1),
                    prediction_confidence=0.8,
                    recommendations=[
                        f"Review account {account_id} configuration and limits",
                        "Analyze trading patterns for this specific account",
                        "Consider account-specific risk parameters",
                        "Investigate account-specific external factors"
                    ]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def detect_agent_patterns(self) -> List[FailurePattern]:
        """Detect agent-specific failure patterns"""
        patterns = []
        
        # Group by agent
        agent_failures = defaultdict(list)
        for event in self.events_history:
            agent_failures[event.agent_name].append(event)
        
        for agent_name, events in agent_failures.items():
            if len(events) >= self.pattern_min_frequency:
                reasons = Counter(event.trigger_reason for event in events)
                accounts = list(set(event.account_id for event in events))
                
                pattern = FailurePattern(
                    pattern_id=f"agent_{agent_name}_pattern",
                    pattern_type=PatternType.CORRELATED_FAILURE,
                    frequency=len(events),
                    affected_accounts=accounts,
                    affected_agents=[agent_name],
                    common_triggers=list(reasons.keys()),
                    time_pattern={
                        'type': 'agent_specific',
                        'failure_frequency': len(events) / self.analysis_window.days,
                        'most_common_reason': reasons.most_common(1)[0][0],
                        'affected_accounts_count': len(accounts)
                    },
                    duration_stats={},
                    recovery_stats={},
                    severity_score=self.calculate_severity_score(len(events), len(accounts)),
                    prediction_confidence=0.85,
                    recommendations=[
                        f"Review {agent_name} agent implementation and thresholds",
                        "Analyze agent-specific metrics and performance",
                        "Consider agent-specific optimizations",
                        "Review agent interaction patterns with other components"
                    ]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def detect_metric_correlation_patterns(self) -> List[FailurePattern]:
        """Detect patterns based on metric correlations"""
        patterns = []
        
        # Extract metrics before failures
        metrics_data = []
        for event in self.events_history:
            if event.metrics_before:
                metrics_data.append({
                    'timestamp': event.timestamp,
                    'account_id': event.account_id,
                    'agent_name': event.agent_name,
                    **event.metrics_before
                })
        
        if not metrics_data:
            return patterns
        
        df = pd.DataFrame(metrics_data)
        
        # Use clustering to find groups of similar metric patterns
        metric_columns = [col for col in df.columns if col not in ['timestamp', 'account_id', 'agent_name']]
        
        if len(metric_columns) >= 2 and len(df) >= 5:
            # Prepare data for clustering
            X = df[metric_columns].fillna(0)
            X_scaled = self.scaler.fit_transform(X)
            
            # DBSCAN clustering
            clustering = DBSCAN(eps=self.clustering_eps, min_samples=2)
            cluster_labels = clustering.fit_predict(X_scaled)
            
            # Analyze clusters
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # Noise points
                    continue
                
                cluster_mask = cluster_labels == cluster_id
                cluster_events = df[cluster_mask]
                
                if len(cluster_events) >= self.pattern_min_frequency:
                    # Calculate cluster characteristics
                    cluster_metrics = X.iloc[cluster_mask].mean().to_dict()
                    
                    pattern = FailurePattern(
                        pattern_id=f"metric_cluster_{cluster_id}",
                        pattern_type=PatternType.CORRELATED_FAILURE,
                        frequency=len(cluster_events),
                        affected_accounts=cluster_events['account_id'].unique().tolist(),
                        affected_agents=cluster_events['agent_name'].unique().tolist(),
                        common_triggers=[],
                        time_pattern={
                            'type': 'metric_correlation',
                            'cluster_id': cluster_id,
                            'characteristic_metrics': cluster_metrics
                        },
                        duration_stats={},
                        recovery_stats={},
                        severity_score=self.calculate_severity_score(len(cluster_events), len(cluster_events['account_id'].unique())),
                        prediction_confidence=0.7,
                        recommendations=[
                            "Investigate correlation between metrics leading to failures",
                            "Consider adjusting thresholds based on metric combinations",
                            "Implement predictive monitoring for this metric pattern"
                        ]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def train_prediction_model(self) -> None:
        """Train ML model for failure prediction"""
        logger.info("Training failure prediction model...")
        
        if not self.events_history:
            await self.collect_circuit_breaker_events()
        
        # Prepare training data
        training_data = []
        labels = []
        
        for event in self.events_history:
            if event.metrics_before:
                # Features: metrics before failure + time features
                features = list(event.metrics_before.values())
                features.extend([
                    event.timestamp.hour,
                    event.timestamp.weekday(),
                    event.timestamp.day
                ])
                
                training_data.append(features)
                labels.append(1)  # Failure occurred
                
                # Create negative samples (no failure)
                # Sample from times when no failures occurred
                for _ in range(2):  # 2 negative samples per positive
                    non_failure_time = event.timestamp - timedelta(hours=np.random.randint(1, 24))
                    non_failure_features = list(event.metrics_before.values())  # Assume similar metrics
                    non_failure_features = [f * np.random.uniform(0.8, 1.2) for f in non_failure_features]  # Add noise
                    non_failure_features.extend([
                        non_failure_time.hour,
                        non_failure_time.weekday(),
                        non_failure_time.day
                    ])
                    
                    training_data.append(non_failure_features)
                    labels.append(0)  # No failure
        
        if len(training_data) < 10:
            logger.warning("Insufficient training data for prediction model")
            return
        
        X = np.array(training_data)
        y = np.array(labels)
        
        # Train Random Forest model
        self.prediction_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.prediction_model.fit(X, y)
        
        # Evaluate model
        predictions = self.prediction_model.predict(X)
        logger.info(f"Model training completed. Accuracy: {np.mean(predictions == y):.3f}")
    
    async def predict_failures(self) -> List[PredictionResult]:
        """Predict potential circuit breaker activations"""
        if not self.prediction_model:
            await self.train_prediction_model()
        
        if not self.prediction_model:
            return []
        
        predictions = []
        
        # Get current metrics for all accounts/agents
        current_time = datetime.utcnow()
        
        # For each active account/agent combination, predict failure probability
        active_accounts = await self.get_active_accounts()
        active_agents = await self.get_active_agents()
        
        for account_id in active_accounts:
            for agent_name in active_agents:
                try:
                    current_metrics = await self.collect_current_metrics(account_id, agent_name)
                    
                    if current_metrics:
                        # Prepare features
                        features = list(current_metrics.values())
                        features.extend([
                            current_time.hour,
                            current_time.weekday(),
                            current_time.day
                        ])
                        
                        # Predict
                        prob = self.prediction_model.predict_proba([features])[0][1]  # Probability of failure
                        
                        if prob > 0.5:  # High probability of failure
                            # Determine contributing factors
                            feature_importance = self.prediction_model.feature_importances_
                            metric_names = list(current_metrics.keys()) + ['hour', 'weekday', 'day']
                            
                            important_factors = [
                                metric_names[i] for i in np.argsort(feature_importance)[-3:]
                            ]
                            
                            prediction = PredictionResult(
                                account_id=account_id,
                                agent_name=agent_name,
                                predicted_failure_time=current_time + self.prediction_horizon,
                                failure_probability=prob,
                                predicted_category=self.predict_failure_category(current_metrics),
                                confidence_score=min(prob * 1.5, 1.0),  # Adjust confidence
                                contributing_factors=important_factors,
                                preventive_actions=self.generate_preventive_actions(important_factors, current_metrics)
                            )
                            
                            predictions.append(prediction)
                
                except Exception as e:
                    logger.error(f"Error predicting for {account_id}/{agent_name}: {e}")
        
        return predictions
    
    def categorize_failure(self, reason: str) -> FailureCategory:
        """Categorize failure based on trigger reason"""
        reason_lower = reason.lower()
        
        if any(keyword in reason_lower for keyword in ['latency', 'timeout', 'slow']):
            return FailureCategory.PERFORMANCE_DEGRADATION
        elif any(keyword in reason_lower for keyword in ['risk', 'drawdown', 'loss']):
            return FailureCategory.RISK_THRESHOLD_BREACH
        elif any(keyword in reason_lower for keyword in ['connection', 'network', 'api']):
            return FailureCategory.CONNECTIVITY_ISSUE
        elif any(keyword in reason_lower for keyword in ['memory', 'cpu', 'resource']):
            return FailureCategory.RESOURCE_EXHAUSTION
        elif any(keyword in reason_lower for keyword in ['compliance', 'rule', 'violation']):
            return FailureCategory.COMPLIANCE_VIOLATION
        elif any(keyword in reason_lower for keyword in ['broker', 'external', 'dependency']):
            return FailureCategory.EXTERNAL_DEPENDENCY
        else:
            return FailureCategory.UNKNOWN
    
    def calculate_severity_score(self, frequency: int, scope: int) -> float:
        """Calculate severity score based on frequency and scope"""
        # Normalize frequency (max expected: 10 failures per week)
        frequency_score = min(frequency / 10.0, 1.0)
        
        # Normalize scope (max expected: 10 accounts affected)
        scope_score = min(scope / 10.0, 1.0)
        
        # Weighted combination
        return (frequency_score * 0.6) + (scope_score * 0.4)
    
    def predict_failure_category(self, metrics: Dict[str, float]) -> FailureCategory:
        """Predict failure category based on current metrics"""
        # Simple rule-based prediction
        if metrics.get('latency_p95', 0) > 0.08:  # 80ms
            return FailureCategory.PERFORMANCE_DEGRADATION
        elif metrics.get('memory_usage', 0) > 0.9:  # 90%
            return FailureCategory.RESOURCE_EXHAUSTION
        elif metrics.get('error_rate', 0) > 0.05:  # 5%
            return FailureCategory.CONNECTIVITY_ISSUE
        else:
            return FailureCategory.UNKNOWN
    
    def generate_preventive_actions(self, factors: List[str], metrics: Dict[str, float]) -> List[str]:
        """Generate preventive actions based on contributing factors"""
        actions = []
        
        for factor in factors:
            if 'latency' in factor:
                actions.append("Scale processing resources")
                actions.append("Optimize database queries")
            elif 'memory' in factor:
                actions.append("Restart services to clear memory")
                actions.append("Investigate memory leaks")
            elif 'error' in factor:
                actions.append("Check external API status")
                actions.append("Review connection pools")
            elif 'cpu' in factor:
                actions.append("Scale compute resources")
                actions.append("Optimize CPU-intensive operations")
        
        if not actions:
            actions.append("Monitor system closely")
            actions.append("Prepare for manual intervention")
        
        return list(set(actions))  # Remove duplicates
    
    async def query_prometheus_range(self, query: str, start_time: datetime, 
                                   end_time: datetime, step: str = "5m") -> List[Dict]:
        """Query Prometheus for range data"""
        url = f"{self.prometheus_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("result", [])
                    return []
        except Exception as e:
            logger.error(f"Failed to query Prometheus: {e}")
            return []
    
    async def collect_event_metrics(self, account_id: str, agent_name: str, 
                                  event_time: datetime) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Collect metrics before and after circuit breaker event"""
        before_time = event_time - timedelta(minutes=5)
        after_time = event_time + timedelta(minutes=5)
        
        metrics_before = {}
        metrics_after = {}
        
        for metric_name, query in self.leading_indicators.items():
            # Get metrics before event
            before_data = await self.query_prometheus_range(
                query, before_time - timedelta(minutes=1), before_time, "1m"
            )
            
            if before_data and before_data[0].get("values"):
                metrics_before[metric_name] = float(before_data[0]["values"][-1][1])
            
            # Get metrics after event
            after_data = await self.query_prometheus_range(
                query, after_time, after_time + timedelta(minutes=1), "1m"
            )
            
            if after_data and after_data[0].get("values"):
                metrics_after[metric_name] = float(after_data[0]["values"][0][1])
        
        return metrics_before, metrics_after
    
    async def calculate_recovery_time(self, account_id: str, event_time: datetime) -> Optional[timedelta]:
        """Calculate recovery time for circuit breaker"""
        # Query for circuit breaker state changes
        recovery_query = f'tmt_circuit_breaker_state{{account_id="{account_id}"}}'
        
        end_time = event_time + timedelta(hours=2)  # Look up to 2 hours ahead
        
        recovery_data = await self.query_prometheus_range(
            recovery_query, event_time, end_time, "1m"
        )
        
        if recovery_data:
            for timestamp, value in recovery_data[0].get("values", []):
                if float(value) == 0:  # Circuit breaker closed (recovered)
                    recovery_time = datetime.fromtimestamp(timestamp)
                    return recovery_time - event_time
        
        return None
    
    async def collect_current_metrics(self, account_id: str, agent_name: str) -> Dict[str, float]:
        """Collect current metrics for prediction"""
        current_metrics = {}
        
        for metric_name, query in self.leading_indicators.items():
            # Modify query to filter by account/agent if possible
            filtered_query = query
            if "account_id" in query or "{" in query:
                # Add label filters if the metric supports them
                if "{" in query:
                    filter_part = f'account_id="{account_id}"'
                    filtered_query = query.replace("{", f"{{{filter_part},")
            
            data = await self.query_prometheus_range(
                filtered_query, 
                datetime.utcnow() - timedelta(minutes=1), 
                datetime.utcnow(), 
                "1m"
            )
            
            if data and data[0].get("values"):
                current_metrics[metric_name] = float(data[0]["values"][-1][1])
        
        return current_metrics
    
    async def get_active_accounts(self) -> List[str]:
        """Get list of active trading accounts"""
        query = "group by (account_id) (tmt_account_active)"
        
        data = await self.query_prometheus_range(
            query, 
            datetime.utcnow() - timedelta(minutes=5), 
            datetime.utcnow(), 
            "5m"
        )
        
        accounts = []
        for series in data:
            account_id = series.get("metric", {}).get("account_id")
            if account_id:
                accounts.append(account_id)
        
        return accounts or ["ACC001", "ACC002", "ACC003"]  # Fallback
    
    async def get_active_agents(self) -> List[str]:
        """Get list of active agents"""
        return [
            "circuit-breaker", "compliance", "wyckoff", "aria-risk",
            "execution", "anti-correlation", "human-behavior", "continuous-improvement"
        ]
    
    async def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        logger.info("Generating circuit breaker analytics report...")
        
        # Collect data if not already done
        if not self.events_history:
            await self.collect_circuit_breaker_events()
        
        if not self.patterns:
            await self.analyze_failure_patterns()
        
        # Get predictions
        predictions = await self.predict_failures()
        
        # Calculate summary statistics
        total_events = len(self.events_history)
        unique_accounts = len(set(event.account_id for event in self.events_history))
        unique_agents = len(set(event.agent_name for event in self.events_history))
        
        failure_categories = Counter(event.failure_category.value for event in self.events_history)
        
        # Calculate MTTR (Mean Time To Recovery)
        recovery_times = [
            event.recovery_time.total_seconds() / 60 
            for event in self.events_history 
            if event.recovery_time
        ]
        
        mttr = np.mean(recovery_times) if recovery_times else 0
        
        report = {
            "summary": {
                "total_circuit_breaker_events": total_events,
                "unique_accounts_affected": unique_accounts,
                "unique_agents_affected": unique_agents,
                "analysis_period_days": self.analysis_window.days,
                "mean_time_to_recovery_minutes": mttr,
                "failure_rate_per_day": total_events / self.analysis_window.days
            },
            "failure_distribution": dict(failure_categories),
            "detected_patterns": [asdict(pattern) for pattern in self.patterns],
            "predictions": [asdict(prediction) for prediction in predictions],
            "recommendations": self.generate_system_recommendations(),
            "report_timestamp": datetime.utcnow().isoformat()
        }
        
        return report
    
    def generate_system_recommendations(self) -> List[str]:
        """Generate system-wide recommendations based on analysis"""
        recommendations = []
        
        if not self.events_history:
            return ["Insufficient data for recommendations"]
        
        # Analyze most common failure categories
        categories = Counter(event.failure_category.value for event in self.events_history)
        most_common = categories.most_common(1)[0][0] if categories else None
        
        if most_common == FailureCategory.PERFORMANCE_DEGRADATION.value:
            recommendations.extend([
                "Focus on performance optimization initiatives",
                "Implement predictive scaling based on latency metrics",
                "Review and optimize database query performance"
            ])
        elif most_common == FailureCategory.RISK_THRESHOLD_BREACH.value:
            recommendations.extend([
                "Review risk management parameters",
                "Implement dynamic risk adjustment based on market conditions",
                "Consider account-specific risk profiles"
            ])
        elif most_common == FailureCategory.CONNECTIVITY_ISSUE.value:
            recommendations.extend([
                "Improve external API resilience",
                "Implement circuit breaker patterns for external dependencies",
                "Review network infrastructure and redundancy"
            ])
        
        # Pattern-based recommendations
        if any(pattern.pattern_type == PatternType.CASCADING_FAILURE for pattern in self.patterns):
            recommendations.append("Implement bulkhead pattern to prevent cascade failures")
        
        if any(pattern.pattern_type == PatternType.PERIODIC_FAILURE for pattern in self.patterns):
            recommendations.append("Investigate and address recurring temporal patterns")
        
        # Add general recommendations
        recommendations.extend([
            "Regularly review and update circuit breaker thresholds",
            "Implement chaos engineering practices to test system resilience",
            "Enhance monitoring and alerting for early failure detection"
        ])
        
        return list(set(recommendations))  # Remove duplicates


async def main():
    """Main function to run circuit breaker analytics"""
    analytics = CircuitBreakerAnalytics()
    
    # Generate comprehensive report
    report = await analytics.generate_analytics_report()
    
    # Save report
    with open(f"circuit_breaker_analytics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info("Circuit breaker analytics completed")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())