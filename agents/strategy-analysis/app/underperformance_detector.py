"""
Underperformance detection system for trading strategies.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio

from .models import (
    TradingStrategy, UnderperformanceDetection, PerformanceIssue,
    SeverityAssessment, RecommendationSet, AutomaticActions,
    RehabilitationPlan, PerformanceIssueType, SeverityLevel,
    ImpactLevel, RecommendedAction, RecoveryPhase, TrendDirection
)

logger = logging.getLogger(__name__)


class UnderperformanceDetector:
    """
    Detects strategy underperformance and recommends corrective actions.
    Implements multiple detection algorithms and automatic response mechanisms.
    """
    
    def __init__(self):
        # Performance thresholds for detection
        self.thresholds = {
            'min_sharpe_ratio': Decimal('0.5'),
            'max_drawdown': Decimal('0.15'),        # 15%
            'min_win_rate': Decimal('0.45'),        # 45%
            'min_profit_factor': Decimal('1.2'),
            'min_expectancy': Decimal('0.001'),     # Positive expectancy required
            'max_consecutive_losses': 10,
            'min_trades_for_evaluation': 30,
            'min_evaluation_period_days': 30
        }
        
        # Severity scoring weights
        self.severity_weights = {
            PerformanceIssueType.HIGH_DRAWDOWN: Decimal('3.0'),
            PerformanceIssueType.POOR_RISK_REWARD: Decimal('2.5'),
            PerformanceIssueType.LOW_WIN_RATE: Decimal('2.0'),
            PerformanceIssueType.INCONSISTENT_PERFORMANCE: Decimal('2.0'),
            PerformanceIssueType.REGIME_MISMATCH: Decimal('1.5')
        }
        
        # Action thresholds
        self.action_thresholds = {
            'monitor': Decimal('20'),      # 0-20% severity
            'reduce_allocation': Decimal('40'),  # 20-40% severity
            'suspend': Decimal('70'),      # 40-70% severity
            'disable': Decimal('100')      # 70-100% severity
        }
    
    async def detect_underperformance(self, strategy: TradingStrategy) -> Optional[UnderperformanceDetection]:
        """
        Detect if a strategy is underperforming and needs intervention.
        
        Args:
            strategy: Trading strategy to evaluate
            
        Returns:
            UnderperformanceDetection if issues found, None otherwise
        """
        logger.info(f"Detecting underperformance for strategy {strategy.strategy_id}")
        
        performance = strategy.performance.overall
        
        # Check minimum sample size
        if performance.total_trades < self.thresholds['min_trades_for_evaluation']:
            logger.debug(f"Insufficient trades ({performance.total_trades}) for strategy {strategy.strategy_id}")
            return None
        
        # Detect performance issues
        issues = await self._detect_performance_issues(strategy)
        
        if not issues:
            logger.debug(f"No performance issues detected for strategy {strategy.strategy_id}")
            return None
        
        # Assess severity
        severity = self._assess_severity(issues)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(strategy, issues, severity)
        
        # Determine automatic actions
        automatic_actions = await self._determine_automatic_actions(strategy, severity)
        
        detection = UnderperformanceDetection(
            detection_id=f"detection_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=strategy.strategy_id,
            timestamp=datetime.utcnow(),
            detection_type="comprehensive_analysis",
            threshold=self._get_primary_threshold(issues),
            evaluation_period=strategy.configuration.evaluation_period,
            minimum_trades=self.thresholds['min_trades_for_evaluation'],
            issues=issues,
            severity=severity,
            recommendations=recommendations,
            automatic_actions=automatic_actions
        )
        
        logger.warning(f"Underperformance detected for strategy {strategy.strategy_id}: "
                      f"{len(issues)} issues, severity {severity.level}")
        
        return detection
    
    async def _detect_performance_issues(self, strategy: TradingStrategy) -> List[PerformanceIssue]:
        """Detect specific performance issues with the strategy."""
        
        issues = []
        performance = strategy.performance.overall
        
        # Check Sharpe ratio
        if performance.sharpe_ratio < self.thresholds['min_sharpe_ratio']:
            issue = self._create_performance_issue(
                issue_type=PerformanceIssueType.POOR_RISK_REWARD,
                description=f"Sharpe ratio {performance.sharpe_ratio:.3f} below threshold {self.thresholds['min_sharpe_ratio']}",
                current_value=performance.sharpe_ratio,
                expected_value=self.thresholds['min_sharpe_ratio'],
                threshold=self.thresholds['min_sharpe_ratio'],
                strategy=strategy
            )
            issues.append(issue)
        
        # Check maximum drawdown
        if performance.max_drawdown > self.thresholds['max_drawdown']:
            issue = self._create_performance_issue(
                issue_type=PerformanceIssueType.HIGH_DRAWDOWN,
                description=f"Max drawdown {performance.max_drawdown:.1%} exceeds threshold {self.thresholds['max_drawdown']:.1%}",
                current_value=performance.max_drawdown,
                expected_value=self.thresholds['max_drawdown'],
                threshold=self.thresholds['max_drawdown'],
                strategy=strategy
            )
            issues.append(issue)
        
        # Check win rate
        if performance.win_rate < self.thresholds['min_win_rate']:
            issue = self._create_performance_issue(
                issue_type=PerformanceIssueType.LOW_WIN_RATE,
                description=f"Win rate {performance.win_rate:.1%} below threshold {self.thresholds['min_win_rate']:.1%}",
                current_value=performance.win_rate,
                expected_value=self.thresholds['min_win_rate'],
                threshold=self.thresholds['min_win_rate'],
                strategy=strategy
            )
            issues.append(issue)
        
        # Check profit factor
        if performance.profit_factor < self.thresholds['min_profit_factor']:
            issue = self._create_performance_issue(
                issue_type=PerformanceIssueType.POOR_RISK_REWARD,
                description=f"Profit factor {performance.profit_factor:.2f} below threshold {self.thresholds['min_profit_factor']}",
                current_value=performance.profit_factor,
                expected_value=self.thresholds['min_profit_factor'],
                threshold=self.thresholds['min_profit_factor'],
                strategy=strategy
            )
            issues.append(issue)
        
        # Check expectancy
        if performance.expectancy < self.thresholds['min_expectancy']:
            issue = self._create_performance_issue(
                issue_type=PerformanceIssueType.POOR_RISK_REWARD,
                description=f"Negative expectancy {performance.expectancy:.4f}",
                current_value=performance.expectancy,
                expected_value=self.thresholds['min_expectancy'],
                threshold=self.thresholds['min_expectancy'],
                strategy=strategy
            )
            issues.append(issue)
        
        # Check performance consistency
        consistency_issue = await self._check_performance_consistency(strategy)
        if consistency_issue:
            issues.append(consistency_issue)
        
        # Check regime mismatch
        regime_issue = await self._check_regime_mismatch(strategy)
        if regime_issue:
            issues.append(regime_issue)
        
        return issues
    
    def _create_performance_issue(self, issue_type: PerformanceIssueType,
                                description: str, current_value: Decimal,
                                expected_value: Decimal, threshold: Decimal,
                                strategy: TradingStrategy) -> PerformanceIssue:
        """Create a performance issue object."""
        
        # Calculate deviation magnitude
        deviation_magnitude = abs(current_value - expected_value) / expected_value if expected_value != 0 else abs(current_value)
        
        # Determine severity based on deviation
        if deviation_magnitude > Decimal('0.5'):  # 50% deviation
            severity = SeverityLevel.SEVERE
        elif deviation_magnitude > Decimal('0.25'):  # 25% deviation
            severity = SeverityLevel.MODERATE
        else:
            severity = SeverityLevel.MINOR
        
        # Determine trend
        trend = self._determine_performance_trend(strategy)
        
        # Calculate trend duration (simplified)
        trend_duration = 30  # Default 30 days
        
        # Calculate impact on portfolio (simplified)
        portfolio_impact = deviation_magnitude * strategy.configuration.weight
        
        # Calculate risk contribution (simplified)
        risk_contribution = deviation_magnitude * Decimal('0.1')
        
        return PerformanceIssue(
            issue_type=issue_type,
            description=description,
            severity=severity,
            current_value=current_value,
            expected_value=expected_value,
            threshold=threshold,
            deviation_magnitude=deviation_magnitude,
            trend=trend,
            trend_duration=trend_duration,
            impact_on_portfolio=portfolio_impact,
            risk_contribution=risk_contribution
        )
    
    def _determine_performance_trend(self, strategy: TradingStrategy) -> TrendDirection:
        """Determine the trend direction of strategy performance."""
        # Use the trend from strategy performance analysis
        if hasattr(strategy.performance, 'trend'):
            return strategy.performance.trend.direction
        
        # Fallback to stable if no trend data
        return TrendDirection.STABLE
    
    async def _check_performance_consistency(self, strategy: TradingStrategy) -> Optional[PerformanceIssue]:
        """Check for inconsistent performance patterns."""
        
        # Check if we have time-based performance data
        if not hasattr(strategy.performance, 'time_based'):
            return None
        
        time_based = strategy.performance.time_based
        
        # Calculate coefficient of variation for monthly performance
        monthly_returns = []
        for month_data in time_based.monthly.values():
            monthly_returns.append(month_data.pnl)
        
        if len(monthly_returns) < 3:  # Need at least 3 months
            return None
        
        # Calculate CV (standard deviation / mean)
        mean_return = sum(monthly_returns) / len(monthly_returns)
        if mean_return == 0:
            return None
        
        variance = sum((r - mean_return) ** 2 for r in monthly_returns) / (len(monthly_returns) - 1)
        std_dev = variance ** Decimal('0.5')
        
        cv = std_dev / abs(mean_return)
        
        # High CV indicates inconsistent performance
        if cv > Decimal('2.0'):  # CV > 2.0 considered highly inconsistent
            return self._create_performance_issue(
                issue_type=PerformanceIssueType.INCONSISTENT_PERFORMANCE,
                description=f"High performance inconsistency (CV: {cv:.2f})",
                current_value=cv,
                expected_value=Decimal('1.0'),
                threshold=Decimal('2.0'),
                strategy=strategy
            )
        
        return None
    
    async def _check_regime_mismatch(self, strategy: TradingStrategy) -> Optional[PerformanceIssue]:
        """Check if strategy is mismatched with current market regime."""
        
        # Check if we have regime performance data
        if not hasattr(strategy.performance, 'regime_performance'):
            return None
        
        regime_performance = strategy.performance.regime_performance
        
        if not regime_performance:
            return None
        
        # Find worst performing regime
        worst_regime = None
        worst_performance = None
        
        for regime, perf_data in regime_performance.items():
            if worst_performance is None or perf_data.performance.expectancy < worst_performance:
                worst_regime = regime
                worst_performance = perf_data.performance.expectancy
        
        # If worst regime has significantly negative performance
        if worst_performance is not None and worst_performance < Decimal('-0.01'):  # -1% expectancy
            return self._create_performance_issue(
                issue_type=PerformanceIssueType.REGIME_MISMATCH,
                description=f"Poor performance in {worst_regime} regime (expectancy: {worst_performance:.3f})",
                current_value=worst_performance,
                expected_value=Decimal('0'),
                threshold=Decimal('-0.01'),
                strategy=strategy
            )
        
        return None
    
    def _assess_severity(self, issues: List[PerformanceIssue]) -> SeverityAssessment:
        """Assess overall severity of performance issues."""
        
        if not issues:
            return SeverityAssessment(
                level=SeverityLevel.MINOR,
                score=Decimal('0'),
                impact=ImpactLevel.LOW,
                urgency=ImpactLevel.LOW
            )
        
        # Calculate weighted severity score
        total_score = Decimal('0')
        total_weight = Decimal('0')
        
        for issue in issues:
            weight = self.severity_weights.get(issue.issue_type, Decimal('1.0'))
            
            # Convert severity to numeric score
            severity_scores = {
                SeverityLevel.MINOR: Decimal('1'),
                SeverityLevel.MODERATE: Decimal('2'),
                SeverityLevel.SEVERE: Decimal('3')
            }
            
            issue_score = severity_scores.get(issue.severity, Decimal('1'))
            total_score += issue_score * weight * issue.deviation_magnitude
            total_weight += weight
        
        # Normalize score to 0-100 scale
        if total_weight > 0:
            normalized_score = (total_score / total_weight) * Decimal('20')  # Scale factor
            normalized_score = min(normalized_score, Decimal('100'))
        else:
            normalized_score = Decimal('0')
        
        # Determine severity level
        if normalized_score >= Decimal('80'):
            level = SeverityLevel.CRITICAL
            impact = ImpactLevel.HIGH
            urgency = ImpactLevel.HIGH
        elif normalized_score >= Decimal('60'):
            level = SeverityLevel.SEVERE
            impact = ImpactLevel.HIGH
            urgency = ImpactLevel.MEDIUM
        elif normalized_score >= Decimal('30'):
            level = SeverityLevel.MODERATE
            impact = ImpactLevel.MEDIUM
            urgency = ImpactLevel.MEDIUM
        else:
            level = SeverityLevel.MINOR
            impact = ImpactLevel.LOW
            urgency = ImpactLevel.LOW
        
        return SeverityAssessment(
            level=level,
            score=normalized_score,
            impact=impact,
            urgency=urgency
        )
    
    async def _generate_recommendations(self, strategy: TradingStrategy,
                                      issues: List[PerformanceIssue],
                                      severity: SeverityAssessment) -> RecommendationSet:
        """Generate recommendations for addressing performance issues."""
        
        # Determine immediate action based on severity
        if severity.score >= self.action_thresholds['disable']:
            immediate_action = RecommendedAction.DISABLE
        elif severity.score >= self.action_thresholds['suspend']:
            immediate_action = RecommendedAction.SUSPEND
        elif severity.score >= self.action_thresholds['reduce_allocation']:
            immediate_action = RecommendedAction.REDUCE_ALLOCATION
        else:
            immediate_action = RecommendedAction.MONITOR
        
        # Create rehabilitation plan if suspending
        rehabilitation_plan = None
        if immediate_action in [RecommendedAction.SUSPEND, RecommendedAction.DISABLE]:
            rehabilitation_plan = await self._create_rehabilitation_plan(strategy, issues, severity)
        
        # Suggest alternative strategies (simplified)
        alternative_strategies = await self._suggest_alternative_strategies(strategy, issues)
        
        # Determine review timeline
        if severity.level == SeverityLevel.CRITICAL:
            time_to_review = 7   # Daily review
        elif severity.level == SeverityLevel.SEVERE:
            time_to_review = 14  # Bi-weekly review
        elif severity.level == SeverityLevel.MODERATE:
            time_to_review = 30  # Monthly review
        else:
            time_to_review = 90  # Quarterly review
        
        return RecommendationSet(
            immediate_action=immediate_action,
            rehabilitation_plan=rehabilitation_plan,
            alternative_strategies=alternative_strategies,
            time_to_review=time_to_review
        )
    
    async def _create_rehabilitation_plan(self, strategy: TradingStrategy,
                                        issues: List[PerformanceIssue],
                                        severity: SeverityAssessment) -> RehabilitationPlan:
        """Create a rehabilitation plan for underperforming strategy."""
        
        # Determine suspension period based on severity
        if severity.level == SeverityLevel.CRITICAL:
            suspension_period = 90   # 3 months
        elif severity.level == SeverityLevel.SEVERE:
            suspension_period = 60   # 2 months
        else:
            suspension_period = 30   # 1 month
        
        # Define monitoring metrics based on issues
        monitoring_metrics = []
        recovery_thresholds = {}
        
        for issue in issues:
            if issue.issue_type == PerformanceIssueType.HIGH_DRAWDOWN:
                monitoring_metrics.append("max_drawdown")
                recovery_thresholds["max_drawdown"] = self.thresholds['max_drawdown']
            elif issue.issue_type == PerformanceIssueType.LOW_WIN_RATE:
                monitoring_metrics.append("win_rate")
                recovery_thresholds["win_rate"] = self.thresholds['min_win_rate']
            elif issue.issue_type == PerformanceIssueType.POOR_RISK_REWARD:
                monitoring_metrics.append("sharpe_ratio")
                recovery_thresholds["sharpe_ratio"] = self.thresholds['min_sharpe_ratio']
        
        # Default monitoring metrics
        if not monitoring_metrics:
            monitoring_metrics = ["expectancy", "sharpe_ratio", "max_drawdown"]
            recovery_thresholds = {
                "expectancy": self.thresholds['min_expectancy'],
                "sharpe_ratio": self.thresholds['min_sharpe_ratio'],
                "max_drawdown": self.thresholds['max_drawdown']
            }
        
        # Evaluation schedule
        evaluation_schedule = [7, 14, 30, 60]  # Days for checkpoints
        
        # Gradual return steps (allocation percentages)
        gradual_return_steps = [Decimal('0.25'), Decimal('0.5'), Decimal('0.75'), Decimal('1.0')]
        
        return RehabilitationPlan(
            plan_id=f"rehab_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d')}",
            strategy_id=strategy.strategy_id,
            suspension_period=suspension_period,
            monitoring_metrics=monitoring_metrics,
            recovery_thresholds=recovery_thresholds,
            evaluation_schedule=evaluation_schedule,
            current_phase=RecoveryPhase.SUSPENDED,
            progress_score=Decimal('0'),
            metrics_improvement={},
            time_to_full_recovery=suspension_period * 2,  # Conservative estimate
            minimum_performance_period=30,  # 30 days of good performance
            required_metrics=recovery_thresholds,
            manual_approval_required=severity.level == SeverityLevel.CRITICAL,
            gradual_return_steps=gradual_return_steps
        )
    
    async def _suggest_alternative_strategies(self, strategy: TradingStrategy,
                                            issues: List[PerformanceIssue]) -> List[str]:
        """Suggest alternative strategies to replace underperforming one."""
        
        # In production, this would query strategy database for similar but better performing strategies
        alternatives = []
        
        # Suggest based on strategy type
        if strategy.classification.type.value == "trend_following":
            alternatives.extend(["momentum_strategy_v2", "breakout_strategy_enhanced"])
        elif strategy.classification.type.value == "mean_reversion":
            alternatives.extend(["mean_reversion_v3", "bollinger_bands_advanced"])
        elif strategy.classification.type.value == "pattern_recognition":
            alternatives.extend(["pattern_ml_v2", "harmonic_patterns_v4"])
        
        # Generic high-performing alternatives
        alternatives.extend(["diversified_portfolio_strategy", "risk_parity_strategy"])
        
        return alternatives[:3]  # Return top 3 alternatives
    
    async def _determine_automatic_actions(self, strategy: TradingStrategy,
                                         severity: SeverityAssessment) -> AutomaticActions:
        """Determine what automatic actions should be taken."""
        
        suspension_triggered = severity.score >= self.action_thresholds['suspend']
        allocation_reduced = severity.score >= self.action_thresholds['reduce_allocation']
        
        # Determine alerts to send
        alerts_sent = []
        if severity.level in [SeverityLevel.SEVERE, SeverityLevel.CRITICAL]:
            alerts_sent.extend(["risk_manager", "portfolio_manager"])
        if severity.level == SeverityLevel.CRITICAL:
            alerts_sent.append("chief_risk_officer")
        
        manual_review_required = (
            severity.level == SeverityLevel.CRITICAL or
            any(issue.issue_type == PerformanceIssueType.HIGH_DRAWDOWN for issue in issues if hasattr(issues, '__iter__'))
        )
        
        return AutomaticActions(
            suspension_triggered=suspension_triggered,
            allocation_reduced=allocation_reduced,
            alerts_sent=alerts_sent,
            manual_review_required=manual_review_required
        )
    
    def _get_primary_threshold(self, issues: List[PerformanceIssue]) -> Decimal:
        """Get the primary threshold that was breached."""
        if not issues:
            return Decimal('0')
        
        # Return the threshold of the most severe issue
        most_severe = max(issues, key=lambda x: self.severity_weights.get(x.issue_type, Decimal('1')))
        return most_severe.threshold
    
    async def update_rehabilitation_progress(self, rehabilitation_plan: RehabilitationPlan,
                                           current_performance: Dict[str, Decimal]) -> RehabilitationPlan:
        """Update rehabilitation plan progress based on current performance."""
        
        # Calculate progress score based on metric improvements
        progress_metrics = {}
        total_progress = Decimal('0')
        metric_count = 0
        
        for metric, threshold in rehabilitation_plan.required_metrics.items():
            if metric in current_performance:
                current_value = current_performance[metric]
                
                # Calculate improvement (simplified)
                if metric in ["max_drawdown"]:  # Lower is better
                    improvement = max(Decimal('0'), threshold - current_value) / threshold
                else:  # Higher is better
                    improvement = max(Decimal('0'), current_value - threshold) / threshold
                
                progress_metrics[metric] = improvement
                total_progress += min(improvement, Decimal('1'))  # Cap at 100% per metric
                metric_count += 1
        
        # Calculate overall progress score
        if metric_count > 0:
            progress_score = (total_progress / Decimal(metric_count)) * Decimal('100')
        else:
            progress_score = Decimal('0')
        
        # Update rehabilitation plan
        rehabilitation_plan.progress_score = progress_score
        rehabilitation_plan.metrics_improvement = progress_metrics
        
        # Update recovery phase based on progress
        if progress_score >= Decimal('80'):
            rehabilitation_plan.current_phase = RecoveryPhase.FULL_RETURN
        elif progress_score >= Decimal('60'):
            rehabilitation_plan.current_phase = RecoveryPhase.GRADUAL_RETURN
        elif progress_score >= Decimal('40'):
            rehabilitation_plan.current_phase = RecoveryPhase.MONITORING
        else:
            rehabilitation_plan.current_phase = RecoveryPhase.SUSPENDED
        
        # Update time to full recovery estimate
        if progress_score > Decimal('0'):
            days_elapsed = 30  # Simplified - would calculate actual days
            estimated_total_days = days_elapsed * Decimal('100') / progress_score
            rehabilitation_plan.time_to_full_recovery = int(estimated_total_days - days_elapsed)
        
        return rehabilitation_plan