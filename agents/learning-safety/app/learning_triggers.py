"""
Learning Circuit Breaker Triggers

Coordinates all market condition detectors and determines when learning
should be enabled or disabled based on market safety conditions.
"""

from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from market_condition_detector import (
    MarketConditionDetector, 
    MarketConditionAnomaly, 
    MarketData,
    MarketConditionThresholds
)
from news_event_monitor import NewsEventMonitor

logger = logging.getLogger(__name__)


class LearningDecision(Enum):
    """Learning decision outcomes"""
    ALLOW = "allow"
    DENY = "deny"
    MONITOR = "monitor"
    QUARANTINE = "quarantine"


@dataclass
class LearningTriggerDecision:
    """Decision from learning trigger system"""
    decision: LearningDecision
    confidence: float  # 0-1
    reason: str
    
    # Anomalies that influenced decision
    detected_anomalies: List[MarketConditionAnomaly]
    
    # Risk assessment
    risk_score: float  # 0-1, cumulative risk from all anomalies
    severity_breakdown: Dict[str, int]  # Count by severity level
    
    # Action requirements
    quarantine_data: bool
    lockout_duration_minutes: int
    manual_review_required: bool
    
    # Context
    symbol: str
    timestamp: datetime
    
    @property
    def learning_safe(self) -> bool:
        """Whether learning is safe based on decision"""
        return self.decision == LearningDecision.ALLOW


class LearningTriggerEngine:
    """Main engine for learning circuit breaker triggers"""
    
    def __init__(self, 
                 market_thresholds: Optional[MarketConditionThresholds] = None,
                 news_lockout_minutes: int = 60):
        self.market_detector = MarketConditionDetector(market_thresholds)
        self.news_monitor = NewsEventMonitor(news_lockout_minutes)
        
        # Risk scoring weights
        self.severity_weights = {
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "critical": 1.0
        }
        
        # Decision thresholds
        self.risk_thresholds = {
            "monitor": 0.3,   # Above this, require monitoring
            "deny": 0.6,      # Above this, deny learning
            "quarantine": 0.8  # Above this, quarantine data
        }
    
    def evaluate_learning_safety(self, market_data: MarketData) -> LearningTriggerDecision:
        """Evaluate if learning is safe for given market data"""
        all_anomalies = []
        
        # Check market condition anomalies
        market_anomalies = self.market_detector.detect_anomalies(market_data)
        all_anomalies.extend(market_anomalies)
        
        # Check news event lockouts
        news_anomaly = self.news_monitor.check_lockout_status(
            market_data.symbol, market_data.timestamp
        )
        if news_anomaly:
            all_anomalies.append(news_anomaly)
        
        # Calculate risk score and make decision
        risk_score = self._calculate_risk_score(all_anomalies)
        decision = self._make_learning_decision(risk_score, all_anomalies)
        
        # Generate severity breakdown
        severity_breakdown = self._get_severity_breakdown(all_anomalies)
        
        # Determine action requirements
        quarantine_needed = any(anomaly.quarantine_recommended for anomaly in all_anomalies)
        manual_review_needed = self._requires_manual_review(all_anomalies, risk_score)
        lockout_duration = max([anomaly.lockout_duration_minutes for anomaly in all_anomalies], default=0)
        
        # Generate reason
        reason = self._generate_decision_reason(decision, all_anomalies, risk_score)
        
        trigger_decision = LearningTriggerDecision(
            decision=decision,
            confidence=self._calculate_confidence(risk_score, all_anomalies),
            reason=reason,
            detected_anomalies=all_anomalies,
            risk_score=risk_score,
            severity_breakdown=severity_breakdown,
            quarantine_data=quarantine_needed,
            lockout_duration_minutes=lockout_duration,
            manual_review_required=manual_review_needed,
            symbol=market_data.symbol,
            timestamp=market_data.timestamp
        )
        
        # Log decision for monitoring
        self._log_decision(trigger_decision)
        
        return trigger_decision
    
    def _calculate_risk_score(self, anomalies: List[MarketConditionAnomaly]) -> float:
        """Calculate cumulative risk score from all anomalies"""
        if not anomalies:
            return 0.0
            
        total_weighted_risk = 0.0
        max_possible_weight = 0.0
        
        for anomaly in anomalies:
            severity_weight = self.severity_weights[anomaly.severity.value]
            confidence_weighted_risk = anomaly.confidence * severity_weight
            total_weighted_risk += confidence_weighted_risk
            max_possible_weight += severity_weight
        
        # Normalize to 0-1 scale but allow for cumulative effect
        # Multiple anomalies can push risk score higher
        base_risk = total_weighted_risk / max(max_possible_weight, 1.0)
        
        # Apply cumulative multiplier for multiple anomalies
        anomaly_count_multiplier = min(1.5, 1.0 + (len(anomalies) - 1) * 0.2)
        
        return min(1.0, base_risk * anomaly_count_multiplier)
    
    def _make_learning_decision(self, risk_score: float, 
                              anomalies: List[MarketConditionAnomaly]) -> LearningDecision:
        """Make learning decision based on risk score and anomalies"""
        # Check for critical anomalies that always deny learning
        critical_anomalies = [a for a in anomalies if a.severity.value == "critical"]
        if critical_anomalies:
            return LearningDecision.DENY
            
        # Check for high-risk scenarios requiring quarantine
        if risk_score >= self.risk_thresholds["quarantine"]:
            return LearningDecision.QUARANTINE
            
        # Check for medium-risk scenarios denying learning
        if risk_score >= self.risk_thresholds["deny"]:
            return LearningDecision.DENY
            
        # Check for low-risk scenarios requiring monitoring
        if risk_score >= self.risk_thresholds["monitor"]:
            return LearningDecision.MONITOR
            
        # Default to allowing learning
        return LearningDecision.ALLOW
    
    def _requires_manual_review(self, anomalies: List[MarketConditionAnomaly], 
                               risk_score: float) -> bool:
        """Determine if manual review is required"""
        # Always require review for critical anomalies
        if any(a.severity.value == "critical" for a in anomalies):
            return True
            
        # Require review for high risk scores
        if risk_score >= 0.8:
            return True
            
        # Require review for multiple high-severity anomalies
        high_severity_count = sum(1 for a in anomalies if a.severity.value in ["high", "critical"])
        if high_severity_count >= 2:
            return True
            
        return False
    
    def _get_severity_breakdown(self, anomalies: List[MarketConditionAnomaly]) -> Dict[str, int]:
        """Get count of anomalies by severity level"""
        breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for anomaly in anomalies:
            breakdown[anomaly.severity.value] += 1
            
        return breakdown
    
    def _calculate_confidence(self, risk_score: float, 
                            anomalies: List[MarketConditionAnomaly]) -> float:
        """Calculate confidence in the decision"""
        if not anomalies:
            return 1.0  # High confidence in allowing learning when no anomalies
            
        # Base confidence from average anomaly confidence
        avg_anomaly_confidence = sum(a.confidence for a in anomalies) / len(anomalies)
        
        # Adjust based on risk score alignment with thresholds
        if risk_score >= 0.8:
            # High risk - high confidence in denial
            return avg_anomaly_confidence
        elif risk_score <= 0.2:
            # Low risk - high confidence in allowing
            return 1.0 - avg_anomaly_confidence * 0.5
        else:
            # Medium risk - moderate confidence
            return 0.6 + avg_anomaly_confidence * 0.3
    
    def _generate_decision_reason(self, decision: LearningDecision, 
                                anomalies: List[MarketConditionAnomaly], 
                                risk_score: float) -> str:
        """Generate human-readable reason for decision"""
        if not anomalies:
            return f"Risk score: {risk_score:.2f} | No market anomalies detected - learning safe"
            
        anomaly_types = [a.condition_type.value for a in anomalies]
        severity_counts = self._get_severity_breakdown(anomalies)
        
        reason_parts = []
        
        # Add risk score context
        reason_parts.append(f"Risk score: {risk_score:.2f}")
        
        # Add anomaly summary
        if severity_counts["critical"] > 0:
            reason_parts.append(f"{severity_counts['critical']} critical anomalies")
        if severity_counts["high"] > 0:
            reason_parts.append(f"{severity_counts['high']} high-severity anomalies")
        if severity_counts["medium"] > 0:
            reason_parts.append(f"{severity_counts['medium']} medium-severity anomalies")
            
        # Add specific anomaly types
        unique_types = list(set(anomaly_types))
        if len(unique_types) <= 3:
            reason_parts.append(f"Types: {', '.join(unique_types)}")
        else:
            reason_parts.append(f"{len(unique_types)} different anomaly types")
        
        # Add decision context
        decision_context = {
            LearningDecision.ALLOW: "Learning approved with standard monitoring",
            LearningDecision.MONITOR: "Learning approved with enhanced monitoring",
            LearningDecision.DENY: "Learning suspended due to elevated risk", 
            LearningDecision.QUARANTINE: "Learning suspended, data quarantined for review"
        }
        
        reason_parts.append(decision_context[decision])
        
        return " | ".join(reason_parts)
    
    def _log_decision(self, decision: LearningTriggerDecision) -> None:
        """Log learning trigger decision for monitoring"""
        log_level = logging.INFO
        
        if decision.decision in [LearningDecision.DENY, LearningDecision.QUARANTINE]:
            log_level = logging.WARNING
        elif decision.decision == LearningDecision.MONITOR:
            log_level = logging.INFO
            
        logger.log(log_level, 
                  f"Learning trigger decision: {decision.decision.value} | "
                  f"Symbol: {decision.symbol} | "
                  f"Risk: {decision.risk_score:.2f} | "
                  f"Anomalies: {len(decision.detected_anomalies)} | "
                  f"Reason: {decision.reason}")
    
    def get_news_monitor(self) -> NewsEventMonitor:
        """Get access to news event monitor for external event registration"""
        return self.news_monitor