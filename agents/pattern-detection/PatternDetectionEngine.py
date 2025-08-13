"""
Main pattern detection engine orchestrating all detection components
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging

from ClusteringDetector import ClusteringDetector, ClusteringThresholds, ClusteringAnalysis
from PrecisionMonitor import PrecisionMonitor, PrecisionThresholds, PrecisionAnalysis  
from CorrelationTracker import CorrelationTracker, CorrelationThresholds, CorrelationAnalysis
from ConsistencyChecker import ConsistencyChecker, ConsistencyThresholds, ConsistencyAnalysis

logger = logging.getLogger(__name__)


@dataclass
class PatternAlert:
    """Unified pattern detection alert"""
    id: str
    alert_type: str  # 'clustering', 'precision', 'correlation', 'consistency', 'timing'
    severity: str  # 'low', 'medium', 'high', 'critical'
    
    # Alert details
    description: str
    detected_pattern: str
    affected_accounts: List[str]
    detection_time: datetime
    
    # Risk assessment
    risk_level: float  # 0-1
    recommended_actions: List[str]
    urgency: str  # 'immediate', 'within_24h', 'within_week'
    
    # Resolution tracking
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None
    resolution_actions: Optional[List[str]] = None


@dataclass
class StealthReport:
    """Monthly stealth assessment report"""
    report_id: str
    period: Tuple[datetime, datetime]
    
    # Overall assessment
    stealth_score: float  # 0-100, higher = better stealth
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    
    # Component analysis
    clustering_analysis: ClusteringAnalysis
    precision_analysis: PrecisionAnalysis
    correlation_analysis: CorrelationAnalysis
    consistency_analysis: ConsistencyAnalysis
    
    # Recommendations and actions
    recommendations: List[str]
    priority_actions: List[str]
    
    # Trends
    stealth_trend: str  # 'improving', 'stable', 'degrading'
    
    # Summary
    executive_summary: str


@dataclass
class DetectionThresholds:
    """Combined thresholds for all detection components"""
    clustering: ClusteringThresholds = field(default_factory=ClusteringThresholds)
    precision: PrecisionThresholds = field(default_factory=PrecisionThresholds)
    correlation: CorrelationThresholds = field(default_factory=CorrelationThresholds)
    consistency: ConsistencyThresholds = field(default_factory=ConsistencyThresholds)


class PatternDetectionEngine:
    """Main engine coordinating all pattern detection components"""
    
    def __init__(self, thresholds: Optional[DetectionThresholds] = None):
        self.thresholds = thresholds or DetectionThresholds()
        
        # Initialize detection components
        self.clustering_detector = ClusteringDetector(self.thresholds.clustering)
        self.precision_monitor = PrecisionMonitor(self.thresholds.precision)
        self.correlation_tracker = CorrelationTracker(self.thresholds.correlation)
        self.consistency_checker = ConsistencyChecker(self.thresholds.consistency)
        
        # State
        self.active_alerts: List[PatternAlert] = []
        self.analysis_history: List[Dict[str, Any]] = []
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_patterns(
        self,
        account_trades: Dict[str, List[Any]],
        analysis_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive pattern analysis across all detection components
        """
        start_time = datetime.now()
        window = analysis_window or timedelta(hours=24)
        
        # Flatten all trades for single-account analyses
        all_trades = []
        for trades in account_trades.values():
            all_trades.extend(trades)
        
        results = {
            'timestamp': start_time,
            'analysis_window': window,
            'accounts_analyzed': list(account_trades.keys()),
            'total_trades': len(all_trades)
        }
        
        try:
            # 1. Clustering Analysis
            self.logger.info("Performing clustering analysis...")
            clustering_result = self.clustering_detector.analyze_clustering(
                all_trades, window
            )
            results['clustering'] = clustering_result
            
            # 2. Precision Analysis  
            self.logger.info("Performing precision analysis...")
            precision_result = self.precision_monitor.analyze_precision(all_trades)
            results['precision'] = precision_result
            
            # 3. Correlation Analysis
            self.logger.info("Performing correlation analysis...")
            correlation_result = self.correlation_tracker.analyze_correlations(
                account_trades, window
            )
            results['correlation'] = correlation_result
            
            # 4. Consistency Analysis
            self.logger.info("Performing consistency analysis...")
            consistency_result = self.consistency_checker.analyze_consistency(
                all_trades, window
            )
            results['consistency'] = consistency_result
            
            # 5. Calculate Overall Risk Score
            overall_risk = self.calculate_overall_risk(results)
            results['overall_risk_score'] = overall_risk
            
            # 6. Generate Unified Alerts
            alerts = self._generate_unified_alerts(results)
            results['alerts'] = alerts
            self.active_alerts.extend(alerts)
            
            # 7. Generate Consolidated Recommendations
            recommendations = self._generate_consolidated_recommendations(results)
            results['recommendations'] = recommendations
            
            # 8. Store in history
            self.analysis_history.append(results)
            
            self.logger.info(
                f"Pattern analysis completed. Risk score: {overall_risk:.3f}, "
                f"Alerts generated: {len(alerts)}"
            )
            
        except Exception as e:
            self.logger.error(f"Error during pattern analysis: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def calculate_overall_risk(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate weighted overall risk score from all components
        """
        weights = {
            'clustering': 0.25,
            'precision': 0.20,
            'correlation': 0.30,  # Highest weight - most critical
            'consistency': 0.25
        }
        
        risk_scores = []
        
        # Extract risk scores from each component
        if 'clustering' in analysis_results:
            risk_scores.append(analysis_results['clustering'].risk_score * weights['clustering'])
        
        if 'precision' in analysis_results:
            risk_scores.append(analysis_results['precision'].overall_score * weights['precision'])
        
        if 'correlation' in analysis_results:
            risk_scores.append(analysis_results['correlation'].risk_score * weights['correlation'])
        
        if 'consistency' in analysis_results:
            risk_scores.append(analysis_results['consistency'].overall_consistency_score * weights['consistency'])
        
        return sum(risk_scores) if risk_scores else 0.0
    
    def generate_stealth_report(
        self,
        start_date: datetime,
        end_date: datetime,
        account_trades: Dict[str, List[Any]]
    ) -> StealthReport:
        """
        Generate comprehensive monthly stealth report
        """
        report_id = f"STEALTH_{start_date.strftime('%Y%m')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze patterns for the period
        analysis_window = end_date - start_date
        analysis_results = self.analyze_patterns(account_trades, analysis_window)
        
        # Calculate stealth score (inverse of risk)
        stealth_score = max(0, 100 - (analysis_results['overall_risk_score'] * 100))
        
        # Determine risk level
        if stealth_score >= 80:
            risk_level = 'low'
        elif stealth_score >= 60:
            risk_level = 'medium'
        elif stealth_score >= 40:
            risk_level = 'high'
        else:
            risk_level = 'critical'
        
        # Generate trend analysis
        stealth_trend = self._analyze_stealth_trend()
        
        # Create executive summary
        executive_summary = self._create_executive_summary(
            stealth_score, risk_level, analysis_results
        )
        
        # Generate prioritized actions
        priority_actions = self._generate_priority_actions(analysis_results)
        
        return StealthReport(
            report_id=report_id,
            period=(start_date, end_date),
            stealth_score=stealth_score,
            risk_level=risk_level,
            clustering_analysis=analysis_results.get('clustering'),
            precision_analysis=analysis_results.get('precision'),
            correlation_analysis=analysis_results.get('correlation'),
            consistency_analysis=analysis_results.get('consistency'),
            recommendations=analysis_results.get('recommendations', []),
            priority_actions=priority_actions,
            stealth_trend=stealth_trend,
            executive_summary=executive_summary
        )
    
    def _generate_unified_alerts(self, analysis_results: Dict[str, Any]) -> List[PatternAlert]:
        """
        Generate unified alerts from all detection components
        """
        alerts = []
        alert_counter = len(self.active_alerts)
        
        # Clustering alerts
        if 'clustering' in analysis_results:
            clustering = analysis_results['clustering']
            if clustering.suspicious_patterns:
                alert_counter += 1
                severity = 'critical' if clustering.risk_score > 0.8 else 'high' if clustering.risk_score > 0.6 else 'medium'
                
                alerts.append(PatternAlert(
                    id=f"CLUSTER_{alert_counter}",
                    alert_type='clustering',
                    severity=severity,
                    description=f"Suspicious clustering patterns detected",
                    detected_pattern='; '.join(clustering.suspicious_patterns[:3]),
                    affected_accounts=list(set(t.account_id for cluster in clustering.temporal_clusters for t in cluster.trades)),
                    detection_time=datetime.now(),
                    risk_level=clustering.risk_score,
                    recommended_actions=clustering.recommendations[:3],
                    urgency='immediate' if severity == 'critical' else 'within_24h'
                ))
        
        # Precision alerts  
        if 'precision' in analysis_results:
            precision = analysis_results['precision']
            if precision.suspicious:
                alert_counter += 1
                severity = 'critical' if precision.overall_score > 0.4 else 'high' if precision.overall_score > 0.25 else 'medium'
                
                alerts.append(PatternAlert(
                    id=f"PRECISION_{alert_counter}",
                    alert_type='precision',
                    severity=severity,
                    description="Execution precision is too high for human trader",
                    detected_pattern='; '.join([p.description for p in precision.suspicious_patterns[:2]]),
                    affected_accounts=analysis_results.get('accounts_analyzed', []),
                    detection_time=datetime.now(),
                    risk_level=precision.overall_score,
                    recommended_actions=precision.recommendations[:3],
                    urgency='immediate' if severity == 'critical' else 'within_24h'
                ))
        
        # Correlation alerts
        if 'correlation' in analysis_results:
            correlation = analysis_results['correlation']
            for corr_alert in correlation.active_alerts:
                alert_counter += 1
                
                alerts.append(PatternAlert(
                    id=f"CORR_{alert_counter}",
                    alert_type='correlation',
                    severity=corr_alert.severity,
                    description=corr_alert.description,
                    detected_pattern=f"Correlation: {corr_alert.correlation_value:.3f}",
                    affected_accounts=list(corr_alert.account_pair),
                    detection_time=corr_alert.detected_at,
                    risk_level=corr_alert.correlation_value,
                    recommended_actions=corr_alert.recommended_actions,
                    urgency='immediate' if corr_alert.severity == 'emergency' else 'within_24h'
                ))
        
        # Consistency alerts
        if 'consistency' in analysis_results:
            consistency = analysis_results['consistency']
            if consistency.suspicious:
                alert_counter += 1
                severity = 'critical' if consistency.overall_consistency_score > 0.35 else 'high' if consistency.overall_consistency_score > 0.2 else 'medium'
                
                alerts.append(PatternAlert(
                    id=f"CONSISTENCY_{alert_counter}",
                    alert_type='consistency',
                    severity=severity,
                    description="Trading consistency is unnatural for human trader",
                    detected_pattern='; '.join(consistency.suspicious_patterns[:2]),
                    affected_accounts=analysis_results.get('accounts_analyzed', []),
                    detection_time=datetime.now(),
                    risk_level=consistency.overall_consistency_score,
                    recommended_actions=consistency.recommendations[:3],
                    urgency='within_24h'
                ))
        
        return alerts
    
    def _generate_consolidated_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """
        Generate consolidated recommendations from all components
        """
        all_recommendations = set()
        
        # Collect recommendations from all components
        for component in ['clustering', 'precision', 'correlation', 'consistency']:
            if component in analysis_results:
                component_recs = analysis_results[component].recommendations
                all_recommendations.update(component_recs)
        
        # Prioritize and deduplicate
        consolidated = list(all_recommendations)
        
        # Sort by urgency (CRITICAL first, then HIGH, etc.)
        def urgency_sort_key(rec):
            if 'CRITICAL' in rec:
                return 0
            elif 'HIGH' in rec:
                return 1
            elif 'MEDIUM' in rec:
                return 2
            else:
                return 3
        
        consolidated.sort(key=urgency_sort_key)
        
        return consolidated[:10]  # Top 10 recommendations
    
    def _analyze_stealth_trend(self) -> str:
        """
        Analyze trend in stealth scores over time
        """
        if len(self.analysis_history) < 3:
            return 'stable'
        
        # Get last few overall risk scores
        recent_scores = [
            analysis['overall_risk_score'] 
            for analysis in self.analysis_history[-5:]
        ]
        
        # Calculate trend
        if len(recent_scores) >= 2:
            trend_coeff = sum(
                recent_scores[i+1] - recent_scores[i] 
                for i in range(len(recent_scores)-1)
            ) / (len(recent_scores) - 1)
            
            if trend_coeff > 0.05:
                return 'degrading'  # Risk increasing = stealth degrading
            elif trend_coeff < -0.05:
                return 'improving'  # Risk decreasing = stealth improving
        
        return 'stable'
    
    def _create_executive_summary(
        self,
        stealth_score: float,
        risk_level: str,
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        Create executive summary of stealth status
        """
        summary_parts = []
        
        # Overall status
        summary_parts.append(f"Current stealth score: {stealth_score:.1f}/100 ({risk_level.upper()} risk)")
        
        # Key findings
        key_risks = []
        clustering_result = analysis_results.get('clustering')
        if clustering_result and hasattr(clustering_result, 'risk_score') and clustering_result.risk_score > 0.6:
            key_risks.append("trade clustering")
        
        precision_result = analysis_results.get('precision')
        if precision_result and hasattr(precision_result, 'overall_score') and precision_result.overall_score > 0.25:
            key_risks.append("execution precision")
        
        correlation_result = analysis_results.get('correlation')
        if correlation_result and hasattr(correlation_result, 'risk_score') and correlation_result.risk_score > 0.6:
            key_risks.append("account correlation")
        
        consistency_result = analysis_results.get('consistency')
        if consistency_result and hasattr(consistency_result, 'overall_consistency_score') and consistency_result.overall_consistency_score > 0.2:
            key_risks.append("performance consistency")
        
        if key_risks:
            summary_parts.append(f"Primary concerns: {', '.join(key_risks)}")
        else:
            summary_parts.append("No significant pattern detection risks identified")
        
        # Alert summary
        alerts = analysis_results.get('alerts', [])
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        if critical_alerts:
            summary_parts.append(f"{len(critical_alerts)} critical alerts requiring immediate attention")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_priority_actions(self, analysis_results: Dict[str, Any]) -> List[str]:
        """
        Generate prioritized action items
        """
        actions = []
        
        # Critical alerts first
        alerts = analysis_results.get('alerts', [])
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        
        if critical_alerts:
            actions.append("Address critical pattern detection alerts immediately")
        
        # High-risk component actions
        correlation_result = analysis_results.get('correlation')
        if correlation_result and hasattr(correlation_result, 'risk_score') and correlation_result.risk_score > 0.7:
            actions.append("Implement account desynchronization measures")
        
        precision_result = analysis_results.get('precision')
        if precision_result and hasattr(precision_result, 'overall_score') and precision_result.overall_score > 0.3:
            actions.append("Inject variance into execution precision")
        
        clustering_result = analysis_results.get('clustering')
        if clustering_result and hasattr(clustering_result, 'risk_score') and clustering_result.risk_score > 0.7:
            actions.append("Add randomization to trade timing patterns")
        
        consistency_result = analysis_results.get('consistency')
        if consistency_result and hasattr(consistency_result, 'overall_consistency_score') and consistency_result.overall_consistency_score > 0.3:
            actions.append("Introduce performance variation mechanisms")
        
        # General actions
        actions.append("Review and update variance injection parameters")
        actions.append("Monitor pattern detection metrics daily for 7 days")
        
        return actions[:5]  # Top 5 priority actions