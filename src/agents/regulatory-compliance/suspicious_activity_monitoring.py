"""
Suspicious Activity Monitoring System - Story 8.15

Detects and reports suspicious trading activities including:
- Anomaly detection in trading patterns
- Market manipulation indicators
- Insider trading patterns
- Money laundering red flags
- Suspicious Activity Reports (SAR)
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
import statistics
import numpy as np
from collections import defaultdict, deque
import json

logger = structlog.get_logger(__name__)


class SuspicionLevel(Enum):
    """Levels of suspicion"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActivityType(Enum):
    """Types of suspicious activities"""
    UNUSUAL_VOLUME = "unusual_volume"
    RAPID_TRADING = "rapid_trading"
    PUMP_AND_DUMP = "pump_and_dump"
    LAYERING = "layering"
    SPOOFING = "spoofing"
    WASH_TRADING = "wash_trading"
    INSIDER_TRADING = "insider_trading"
    FRONT_RUNNING = "front_running"
    CHURNING = "churning"
    STRUCTURING = "structuring"
    CROSS_ACCOUNT_COORDINATION = "cross_account_coordination"
    UNUSUAL_PROFIT = "unusual_profit"
    TIMING_ANOMALY = "timing_anomaly"


class InvestigationStatus(Enum):
    """Investigation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEWED = "reviewed"
    ESCALATED = "escalated"
    CLOSED_NO_ACTION = "closed_no_action"
    REPORTED_SAR = "reported_sar"


@dataclass
class SuspiciousActivity:
    """Represents a suspicious activity detection"""
    activity_id: str
    account_id: str
    activity_type: ActivityType
    suspicion_level: SuspicionLevel
    detection_time: datetime
    activity_period_start: datetime
    activity_period_end: datetime
    description: str
    indicators: List[str]
    risk_score: float
    related_instruments: List[str]
    related_accounts: Set[str]
    investigation_status: InvestigationStatus = InvestigationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyIndicator:
    """Individual anomaly indicator"""
    indicator_id: str
    indicator_type: str
    threshold: float
    actual_value: float
    severity: float
    description: str
    timestamp: datetime


@dataclass
class TradingPattern:
    """Trading pattern for analysis"""
    account_id: str
    instrument: str
    pattern_date: date
    trade_count: int
    volume: Decimal
    avg_trade_size: Decimal
    time_spread: timedelta
    price_impact: Decimal
    profit_loss: Decimal
    unusual_timing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SARReport:
    """Suspicious Activity Report"""
    sar_id: str
    filing_date: datetime
    subject_account_id: str
    subject_name: str
    suspicious_activities: List[SuspiciousActivity]
    total_dollar_amount: Decimal
    investigation_summary: str
    recommendation: str
    filed_with_fincen: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class SuspiciousActivityMonitoringSystem:
    """Main suspicious activity monitoring system"""
    
    def __init__(self):
        self.suspicious_activities: Dict[str, List[SuspiciousActivity]] = defaultdict(list)
        self.trading_patterns: Dict[str, List[TradingPattern]] = defaultdict(list)
        self.account_baselines: Dict[str, Dict[str, Any]] = {}
        self.sar_reports: List[SARReport] = []
        self.anomaly_detector = AnomalyDetector()
        self.pattern_analyzer = PatternAnalyzer()
        self.investigation_engine = InvestigationEngine()
        self.alert_manager = AlertManager()
        
    async def initialize(self):
        """Initialize suspicious activity monitoring"""
        logger.info("Initializing suspicious activity monitoring system")
        await self.anomaly_detector.initialize()
        await self.pattern_analyzer.initialize()
        await self.investigation_engine.initialize()
        await self.alert_manager.initialize()
        
    async def analyze_trading_activity(self, account_id: str, trades: List[Dict[str, Any]]):
        """Analyze trading activity for suspicious patterns"""
        # Create trading pattern
        pattern = await self._create_trading_pattern(account_id, trades)
        self.trading_patterns[account_id].append(pattern)
        
        # Detect anomalies
        anomalies = await self.anomaly_detector.detect_anomalies(account_id, pattern)
        
        # Analyze patterns
        suspicious_patterns = await self.pattern_analyzer.analyze_patterns(account_id, pattern)
        
        # Check for suspicious activities
        for anomaly in anomalies:
            if anomaly.severity > 0.7:  # High severity threshold
                await self._create_suspicious_activity(account_id, anomaly, trades)
        
        for sus_pattern in suspicious_patterns:
            await self._create_suspicious_activity(account_id, sus_pattern, trades)
            
    async def _create_trading_pattern(self, account_id: str, trades: List[Dict[str, Any]]) -> TradingPattern:
        """Create trading pattern from trades"""
        if not trades:
            return None
            
        trade_date = datetime.fromisoformat(trades[0]['timestamp']).date()
        instruments = set(trade['instrument'] for trade in trades)
        primary_instrument = instruments.pop() if len(instruments) == 1 else 'MIXED'
        
        total_volume = sum(Decimal(str(trade['quantity'])) * Decimal(str(trade['price'])) for trade in trades)
        avg_trade_size = total_volume / len(trades) if trades else Decimal('0')
        
        # Calculate time spread
        timestamps = [datetime.fromisoformat(trade['timestamp']) for trade in trades]
        time_spread = max(timestamps) - min(timestamps) if len(timestamps) > 1 else timedelta(0)
        
        # Calculate profit/loss (simplified)
        profit_loss = sum(Decimal(str(trade.get('profit_loss', 0))) for trade in trades)
        
        # Check for unusual timing (trading outside normal hours)
        unusual_timing = any(
            ts.hour < 9 or ts.hour > 16 for ts in timestamps
        )
        
        pattern = TradingPattern(
            account_id=account_id,
            instrument=primary_instrument,
            pattern_date=trade_date,
            trade_count=len(trades),
            volume=total_volume,
            avg_trade_size=avg_trade_size,
            time_spread=time_spread,
            price_impact=Decimal('0'),  # Would calculate from market data
            profit_loss=profit_loss,
            unusual_timing=unusual_timing
        )
        
        return pattern
        
    async def _create_suspicious_activity(self, account_id: str, indicator: Any, trades: List[Dict[str, Any]]):
        """Create suspicious activity record"""
        if hasattr(indicator, 'indicator_type'):
            # From anomaly detector
            activity_type = self._map_indicator_to_activity_type(indicator.indicator_type)
            description = indicator.description
            risk_score = indicator.severity
            indicators = [indicator.indicator_type]
        else:
            # From pattern analyzer
            activity_type = indicator.get('type', ActivityType.UNUSUAL_VOLUME)
            description = indicator.get('description', 'Suspicious pattern detected')
            risk_score = indicator.get('risk_score', 0.5)
            indicators = indicator.get('indicators', [])
        
        # Determine suspicion level based on risk score
        if risk_score >= 0.9:
            suspicion_level = SuspicionLevel.CRITICAL
        elif risk_score >= 0.7:
            suspicion_level = SuspicionLevel.HIGH
        elif risk_score >= 0.5:
            suspicion_level = SuspicionLevel.MEDIUM
        else:
            suspicion_level = SuspicionLevel.LOW
        
        # Get time period
        timestamps = [datetime.fromisoformat(trade['timestamp']) for trade in trades]
        period_start = min(timestamps) if timestamps else datetime.now()
        period_end = max(timestamps) if timestamps else datetime.now()
        
        # Get related instruments
        related_instruments = list(set(trade['instrument'] for trade in trades))
        
        suspicious_activity = SuspiciousActivity(
            activity_id=f"sa_{account_id}_{datetime.now().timestamp()}",
            account_id=account_id,
            activity_type=activity_type,
            suspicion_level=suspicion_level,
            detection_time=datetime.now(),
            activity_period_start=period_start,
            activity_period_end=period_end,
            description=description,
            indicators=indicators,
            risk_score=risk_score,
            related_instruments=related_instruments,
            related_accounts={account_id}
        )
        
        self.suspicious_activities[account_id].append(suspicious_activity)
        
        # Create alert
        await self.alert_manager.create_alert(suspicious_activity)
        
        logger.warning(f"Suspicious activity detected: {suspicious_activity.activity_id}")
        
    def _map_indicator_to_activity_type(self, indicator_type: str) -> ActivityType:
        """Map indicator type to activity type"""
        mapping = {
            'volume_spike': ActivityType.UNUSUAL_VOLUME,
            'rapid_trading': ActivityType.RAPID_TRADING,
            'unusual_profit': ActivityType.UNUSUAL_PROFIT,
            'timing_anomaly': ActivityType.TIMING_ANOMALY,
            'churning': ActivityType.CHURNING,
            'layering': ActivityType.LAYERING
        }
        return mapping.get(indicator_type, ActivityType.UNUSUAL_VOLUME)
        
    async def investigate_activity(self, activity_id: str) -> Dict[str, Any]:
        """Investigate a suspicious activity"""
        # Find the activity
        activity = None
        for activities in self.suspicious_activities.values():
            for sa in activities:
                if sa.activity_id == activity_id:
                    activity = sa
                    break
            if activity:
                break
        
        if not activity:
            return {'error': 'Activity not found'}
        
        # Start investigation
        investigation_result = await self.investigation_engine.investigate(activity)
        
        # Update activity status
        activity.investigation_status = InvestigationStatus.IN_PROGRESS
        
        return investigation_result
        
    async def generate_sar_report(self, account_id: str, activity_ids: List[str]) -> SARReport:
        """Generate Suspicious Activity Report"""
        # Get suspicious activities
        activities = []
        for activity_id in activity_ids:
            for activities_list in self.suspicious_activities.values():
                for sa in activities_list:
                    if sa.activity_id == activity_id:
                        activities.append(sa)
        
        if not activities:
            raise ValueError("No activities found for SAR report")
        
        # Calculate total dollar amount
        total_amount = Decimal('0')
        for activity in activities:
            # This would be calculated from actual trade data
            total_amount += Decimal('100000')  # Placeholder
        
        sar_report = SARReport(
            sar_id=f"sar_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            filing_date=datetime.now(),
            subject_account_id=account_id,
            subject_name="Account Holder",  # Would get from account data
            suspicious_activities=activities,
            total_dollar_amount=total_amount,
            investigation_summary="Multiple suspicious activities detected requiring SAR filing",
            recommendation="File SAR with FinCEN"
        )
        
        self.sar_reports.append(sar_report)
        
        # Update activity statuses
        for activity in activities:
            activity.investigation_status = InvestigationStatus.REPORTED_SAR
        
        logger.info(f"Generated SAR report: {sar_report.sar_id}")
        return sar_report
        
    async def get_suspicious_activities_summary(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of suspicious activities"""
        if account_id:
            activities = self.suspicious_activities.get(account_id, [])
        else:
            activities = []
            for activities_list in self.suspicious_activities.values():
                activities.extend(activities_list)
        
        # Count by type and level
        type_counts = defaultdict(int)
        level_counts = defaultdict(int)
        status_counts = defaultdict(int)
        
        for activity in activities:
            type_counts[activity.activity_type.value] += 1
            level_counts[activity.suspicion_level.value] += 1
            status_counts[activity.investigation_status.value] += 1
        
        return {
            'total_activities': len(activities),
            'by_type': dict(type_counts),
            'by_level': dict(level_counts),
            'by_status': dict(status_counts),
            'critical_activities': len([a for a in activities if a.suspicion_level == SuspicionLevel.CRITICAL]),
            'pending_investigations': len([a for a in activities if a.investigation_status == InvestigationStatus.PENDING]),
            'sar_reports_filed': len(self.sar_reports)
        }


class AnomalyDetector:
    """Detects trading anomalies"""
    
    def __init__(self):
        self.baseline_window = 30  # Days for baseline calculation
        self.anomaly_threshold = 2.5  # Standard deviations for anomaly
        
    async def initialize(self):
        """Initialize anomaly detector"""
        logger.info("Initialized anomaly detector")
        
    async def detect_anomalies(self, account_id: str, pattern: TradingPattern) -> List[AnomalyIndicator]:
        """Detect anomalies in trading pattern"""
        anomalies = []
        
        # Volume anomaly
        volume_anomaly = await self._detect_volume_anomaly(account_id, pattern)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        # Frequency anomaly
        frequency_anomaly = await self._detect_frequency_anomaly(account_id, pattern)
        if frequency_anomaly:
            anomalies.append(frequency_anomaly)
        
        # Timing anomaly
        if pattern.unusual_timing:
            timing_anomaly = AnomalyIndicator(
                indicator_id=f"timing_{datetime.now().timestamp()}",
                indicator_type="timing_anomaly",
                threshold=0.5,
                actual_value=1.0,
                severity=0.6,
                description="Trading outside normal market hours",
                timestamp=datetime.now()
            )
            anomalies.append(timing_anomaly)
        
        # Profit anomaly
        profit_anomaly = await self._detect_profit_anomaly(account_id, pattern)
        if profit_anomaly:
            anomalies.append(profit_anomaly)
        
        return anomalies
        
    async def _detect_volume_anomaly(self, account_id: str, pattern: TradingPattern) -> Optional[AnomalyIndicator]:
        """Detect volume anomalies"""
        # Get historical volumes for baseline
        historical_patterns = [
            p for p in self.trading_patterns.get(account_id, [])
            if p.pattern_date >= pattern.pattern_date - timedelta(days=self.baseline_window)
            and p.pattern_date < pattern.pattern_date
        ]
        
        if len(historical_patterns) < 5:  # Need minimum baseline
            return None
        
        historical_volumes = [float(p.volume) for p in historical_patterns]
        baseline_mean = statistics.mean(historical_volumes)
        baseline_std = statistics.stdev(historical_volumes) if len(historical_volumes) > 1 else 0
        
        if baseline_std == 0:
            return None
        
        current_volume = float(pattern.volume)
        z_score = abs(current_volume - baseline_mean) / baseline_std
        
        if z_score > self.anomaly_threshold:
            return AnomalyIndicator(
                indicator_id=f"volume_{datetime.now().timestamp()}",
                indicator_type="volume_spike",
                threshold=baseline_mean + (self.anomaly_threshold * baseline_std),
                actual_value=current_volume,
                severity=min(z_score / 5.0, 1.0),  # Normalize to 0-1
                description=f"Trading volume {z_score:.1f} standard deviations above normal",
                timestamp=datetime.now()
            )
        
        return None
        
    async def _detect_frequency_anomaly(self, account_id: str, pattern: TradingPattern) -> Optional[AnomalyIndicator]:
        """Detect trading frequency anomalies"""
        # Check for rapid trading (high frequency in short time)
        if pattern.time_spread.total_seconds() < 3600 and pattern.trade_count > 20:  # 20+ trades in 1 hour
            return AnomalyIndicator(
                indicator_id=f"frequency_{datetime.now().timestamp()}",
                indicator_type="rapid_trading",
                threshold=20.0,
                actual_value=float(pattern.trade_count),
                severity=min(pattern.trade_count / 50.0, 1.0),
                description=f"High frequency trading: {pattern.trade_count} trades in {pattern.time_spread}",
                timestamp=datetime.now()
            )
        
        return None
        
    async def _detect_profit_anomaly(self, account_id: str, pattern: TradingPattern) -> Optional[AnomalyIndicator]:
        """Detect unusual profit patterns"""
        # Detect unusually high profits that might indicate insider trading
        if pattern.profit_loss > pattern.volume * Decimal('0.1'):  # 10% profit in one day
            return AnomalyIndicator(
                indicator_id=f"profit_{datetime.now().timestamp()}",
                indicator_type="unusual_profit",
                threshold=float(pattern.volume * Decimal('0.05')),  # 5% normal threshold
                actual_value=float(pattern.profit_loss),
                severity=0.8,
                description=f"Unusually high profit: {pattern.profit_loss} on volume {pattern.volume}",
                timestamp=datetime.now()
            )
        
        return None


class PatternAnalyzer:
    """Analyzes trading patterns for suspicious behavior"""
    
    def __init__(self):
        self.pattern_window = 10  # Days to analyze for patterns
        
    async def initialize(self):
        """Initialize pattern analyzer"""
        logger.info("Initialized pattern analyzer")
        
    async def analyze_patterns(self, account_id: str, pattern: TradingPattern) -> List[Dict[str, Any]]:
        """Analyze patterns for suspicious behavior"""
        suspicious_patterns = []
        
        # Check for wash trading
        wash_trading = await self._detect_wash_trading(account_id, pattern)
        if wash_trading:
            suspicious_patterns.append(wash_trading)
        
        # Check for layering
        layering = await self._detect_layering(account_id, pattern)
        if layering:
            suspicious_patterns.append(layering)
        
        # Check for churning
        churning = await self._detect_churning(account_id, pattern)
        if churning:
            suspicious_patterns.append(churning)
        
        return suspicious_patterns
        
    async def _detect_wash_trading(self, account_id: str, pattern: TradingPattern) -> Optional[Dict[str, Any]]:
        """Detect wash trading patterns"""
        # Look for simultaneous buy/sell orders of same instrument
        # This is a simplified check - real implementation would be more sophisticated
        
        recent_patterns = [
            p for p in self.trading_patterns.get(account_id, [])
            if abs((p.pattern_date - pattern.pattern_date).days) <= 1
            and p.instrument == pattern.instrument
        ]
        
        if len(recent_patterns) >= 2:
            # Check for offsetting positions
            total_volume = sum(p.volume for p in recent_patterns)
            if total_volume == 0:  # Perfect offset might indicate wash trading
                return {
                    'type': ActivityType.WASH_TRADING,
                    'description': 'Potential wash trading detected - offsetting positions',
                    'risk_score': 0.7,
                    'indicators': ['offsetting_positions', 'same_instrument', 'short_timeframe']
                }
        
        return None
        
    async def _detect_layering(self, account_id: str, pattern: TradingPattern) -> Optional[Dict[str, Any]]:
        """Detect layering/spoofing patterns"""
        # Check for rapid placement and cancellation of orders
        if pattern.trade_count > 15 and pattern.time_spread.total_seconds() < 1800:  # 15+ trades in 30 minutes
            return {
                'type': ActivityType.LAYERING,
                'description': 'Potential layering detected - rapid order placement/cancellation',
                'risk_score': 0.6,
                'indicators': ['rapid_orders', 'short_timeframe', 'high_frequency']
            }
        
        return None
        
    async def _detect_churning(self, account_id: str, pattern: TradingPattern) -> Optional[Dict[str, Any]]:
        """Detect churning patterns"""
        # Look for excessive trading relative to account size
        # This would need account equity data in real implementation
        
        # Check for high turnover in short period
        recent_patterns = [
            p for p in self.trading_patterns.get(account_id, [])
            if abs((p.pattern_date - pattern.pattern_date).days) <= 7
        ]
        
        weekly_volume = sum(p.volume for p in recent_patterns)
        
        # Assuming account equity of $100k for example
        account_equity = Decimal('100000')
        turnover_ratio = weekly_volume / account_equity
        
        if turnover_ratio > 5:  # 500% weekly turnover
            return {
                'type': ActivityType.CHURNING,
                'description': f'Excessive trading detected - {turnover_ratio:.1f}x weekly turnover',
                'risk_score': 0.5,
                'indicators': ['high_turnover', 'excessive_trading']
            }
        
        return None


class InvestigationEngine:
    """Handles investigation of suspicious activities"""
    
    def __init__(self):
        self.investigations: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize investigation engine"""
        logger.info("Initialized investigation engine")
        
    async def investigate(self, activity: SuspiciousActivity) -> Dict[str, Any]:
        """Investigate a suspicious activity"""
        investigation_id = f"inv_{activity.activity_id}"
        
        # Gather additional data
        investigation_data = {
            'investigation_id': investigation_id,
            'activity_id': activity.activity_id,
            'start_time': datetime.now(),
            'investigator': 'System',
            'status': 'in_progress',
            'findings': [],
            'recommendations': []
        }
        
        # Perform investigation steps
        findings = await self._gather_evidence(activity)
        investigation_data['findings'] = findings
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(activity, findings)
        investigation_data['recommendations'] = recommendations
        
        # Determine if escalation is needed
        if activity.suspicion_level == SuspicionLevel.CRITICAL:
            investigation_data['escalation_required'] = True
            investigation_data['escalation_reason'] = 'Critical suspicion level'
        
        self.investigations[investigation_id] = investigation_data
        
        return investigation_data
        
    async def _gather_evidence(self, activity: SuspiciousActivity) -> List[Dict[str, Any]]:
        """Gather evidence for investigation"""
        evidence = []
        
        # Account history evidence
        evidence.append({
            'type': 'account_history',
            'description': f'Account {activity.account_id} trading history analysis',
            'severity': 'medium'
        })
        
        # Pattern evidence
        evidence.append({
            'type': 'pattern_analysis',
            'description': f'Suspicious pattern: {activity.activity_type.value}',
            'severity': activity.suspicion_level.value
        })
        
        # Risk score evidence
        evidence.append({
            'type': 'risk_assessment',
            'description': f'Risk score: {activity.risk_score}',
            'severity': 'high' if activity.risk_score > 0.7 else 'medium'
        })
        
        return evidence
        
    async def _generate_recommendations(self, activity: SuspiciousActivity,
                                       findings: List[Dict[str, Any]]) -> List[str]:
        """Generate investigation recommendations"""
        recommendations = []
        
        if activity.suspicion_level == SuspicionLevel.CRITICAL:
            recommendations.append("Immediately escalate to compliance officer")
            recommendations.append("Consider filing SAR report")
            recommendations.append("Implement enhanced monitoring")
        elif activity.suspicion_level == SuspicionLevel.HIGH:
            recommendations.append("Conduct enhanced due diligence")
            recommendations.append("Monitor account for 30 days")
            recommendations.append("Consider customer outreach")
        else:
            recommendations.append("Continue routine monitoring")
            recommendations.append("Document findings in customer file")
        
        return recommendations


class AlertManager:
    """Manages alerts for suspicious activities"""
    
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize alert manager"""
        logger.info("Initialized alert manager")
        
    async def create_alert(self, activity: SuspiciousActivity):
        """Create alert for suspicious activity"""
        alert = {
            'alert_id': f"alert_{activity.activity_id}",
            'activity_id': activity.activity_id,
            'account_id': activity.account_id,
            'alert_type': 'suspicious_activity',
            'severity': activity.suspicion_level.value,
            'message': f"Suspicious activity detected: {activity.activity_type.value}",
            'description': activity.description,
            'timestamp': datetime.now(),
            'requires_review': activity.suspicion_level in [SuspicionLevel.HIGH, SuspicionLevel.CRITICAL],
            'metadata': {
                'risk_score': activity.risk_score,
                'indicators': activity.indicators,
                'related_instruments': activity.related_instruments
            }
        }
        
        self.alerts.append(alert)
        
        logger.info(f"Created alert: {alert['alert_id']}")
        
        # Send notifications for critical alerts
        if activity.suspicion_level == SuspicionLevel.CRITICAL:
            await self._send_critical_notification(alert)
            
    async def _send_critical_notification(self, alert: Dict[str, Any]):
        """Send notification for critical alerts"""
        # This would send email/SMS/Slack notifications
        logger.critical(f"CRITICAL ALERT: {alert['message']} - Account: {alert['account_id']}")
        
    async def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Get pending alerts requiring review"""
        return [
            alert for alert in self.alerts
            if alert.get('requires_review', False) and not alert.get('reviewed', False)
        ]