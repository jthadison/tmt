"""
Disagreement Logger - Comprehensive audit trail for all disagreement decisions.
Implements AC5: Disagreement logging showing rationale for variance.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from .models import (
    SignalDisagreement, AccountDecision, CorrelationAlert, 
    CorrelationDataPoint, DisagreementProfile
)

logger = logging.getLogger(__name__)


class DisagreementLogger:
    """
    Comprehensive logging system for disagreement decisions and rationale.
    
    Provides audit trails, performance analysis, and human-readable explanations
    for all disagreement decisions made by the system.
    """
    
    def __init__(self, log_directory: str = "logs/disagreements"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup structured logging
        self.disagreement_log_file = self.log_directory / "disagreements.jsonl"
        self.correlation_log_file = self.log_directory / "correlations.jsonl"
        self.summary_log_file = self.log_directory / "summaries.jsonl"
        
        # Performance tracking
        self.performance_metrics = {
            "total_signals": 0,
            "total_decisions": 0,
            "disagreement_count": 0,
            "skip_count": 0,
            "modify_count": 0,
            "correlation_alerts": 0
        }
        
        logger.info(f"DisagreementLogger initialized with directory: {self.log_directory}")

    def log_signal_disagreement(
        self,
        disagreement: SignalDisagreement,
        personalities: Dict[str, DisagreementProfile],
        additional_context: Dict[str, Any] = None
    ) -> None:
        """Log a complete signal disagreement with full context."""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "signal_id": disagreement.signal_id,
            "signal": self._serialize_signal(disagreement.original_signal),
            "decisions": [self._serialize_decision(d) for d in disagreement.account_decisions],
            "metrics": self._serialize_metrics(disagreement.disagreement_metrics),
            "correlation_impact": self._serialize_correlation_impact(disagreement.correlation_impact),
            "human_summary": self._generate_human_summary(disagreement, personalities),
            "additional_context": additional_context or {}
        }
        
        # Write to structured log
        self._write_jsonl_entry(self.disagreement_log_file, log_entry)
        
        # Update performance metrics
        self._update_performance_metrics(disagreement)
        
        logger.info(f"Logged disagreement for signal {disagreement.signal_id}: "
                   f"{len(disagreement.account_decisions)} decisions, "
                   f"{disagreement.disagreement_metrics.participation_rate:.1%} participation")

    def log_correlation_alert(self, alert: CorrelationAlert, context: Dict[str, Any] = None) -> None:
        """Log correlation alert with context."""
        
        log_entry = {
            "timestamp": alert.timestamp.isoformat(),
            "account_pair": alert.account_pair,
            "correlation": alert.correlation,
            "severity": alert.severity.value,
            "recommended_action": alert.recommended_action,
            "context": context or {}
        }
        
        self._write_jsonl_entry(self.correlation_log_file, log_entry)
        self.performance_metrics["correlation_alerts"] += 1
        
        logger.warning(f"Logged correlation alert: {alert.account_pair} = {alert.correlation:.3f} "
                      f"({alert.severity.value})")

    def log_performance_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """Generate and log performance summary for a time period."""
        
        cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        
        # Load recent disagreements
        recent_disagreements = self._load_recent_disagreements(cutoff)
        
        # Calculate summary statistics
        summary = self._calculate_summary_statistics(recent_disagreements, period_hours)
        
        # Log summary
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "period_hours": period_hours,
            "summary": summary,
            "detailed_analysis": self._generate_detailed_analysis(recent_disagreements)
        }
        
        self._write_jsonl_entry(self.summary_log_file, log_entry)
        
        logger.info(f"Generated {period_hours}h performance summary: "
                   f"{summary['total_signals']} signals, "
                   f"{summary['disagreement_rate']:.1%} disagreement rate")
        
        return summary

    def get_disagreement_analysis(
        self,
        account_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get disagreement analysis for an account or overall system."""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_disagreements = self._load_recent_disagreements(cutoff)
        
        if account_id:
            # Filter for specific account
            account_decisions = []
            for disagreement in recent_disagreements:
                account_decisions.extend([
                    d for d in disagreement.account_decisions
                    if d.account_id == account_id
                ])
            
            return self._analyze_account_decisions(account_decisions, account_id)
        else:
            # Overall system analysis
            return self._analyze_system_performance(recent_disagreements)

    def get_correlation_history(
        self,
        account_pair: Optional[str] = None,
        hours: int = 168  # 1 week
    ) -> List[Dict[str, Any]]:
        """Get correlation history for analysis."""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Load correlation entries
        correlation_entries = []
        try:
            with open(self.correlation_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_time >= cutoff:
                        if account_pair is None or entry['account_pair'] == account_pair:
                            correlation_entries.append(entry)
        except FileNotFoundError:
            logger.warning("No correlation log file found")
        
        return correlation_entries

    def generate_human_readable_report(
        self,
        hours: int = 24,
        include_details: bool = True
    ) -> str:
        """Generate human-readable disagreement report."""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_disagreements = self._load_recent_disagreements(cutoff)
        
        if not recent_disagreements:
            return f"No disagreements recorded in the last {hours} hours."
        
        # Generate report sections
        report = []
        report.append(f"DISAGREEMENT ANALYSIS REPORT - Last {hours} Hours")
        report.append("=" * 50)
        report.append("")
        
        # Executive summary
        summary = self._calculate_summary_statistics(recent_disagreements, hours)
        report.append("EXECUTIVE SUMMARY:")
        report.append(f"• Total signals processed: {summary['total_signals']}")
        report.append(f"• Overall disagreement rate: {summary['disagreement_rate']:.1%}")
        report.append(f"• Average participation rate: {summary['avg_participation_rate']:.1%}")
        report.append(f"• Correlation alerts triggered: {summary['correlation_alerts']}")
        report.append("")
        
        # Decision breakdown
        report.append("DECISION BREAKDOWN:")
        report.append(f"• Take decisions: {summary['take_decisions']} ({summary['take_rate']:.1%})")
        report.append(f"• Skip decisions: {summary['skip_decisions']} ({summary['skip_rate']:.1%})")
        report.append(f"• Modify decisions: {summary['modify_decisions']} ({summary['modify_rate']:.1%})")
        report.append("")
        
        # Top disagreement reasons
        if include_details:
            report.append("TOP DISAGREEMENT REASONS:")
            reason_counts = {}
            for disagreement in recent_disagreements:
                for decision in disagreement.account_decisions:
                    if decision.decision.value != 'take':
                        reason = decision.reasoning
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:10]:
                report.append(f"• {reason}: {count} times")
            report.append("")
        
        # Correlation analysis
        if summary.get('high_correlation_pairs', 0) > 0:
            report.append("CORRELATION CONCERNS:")
            report.append(f"• {summary['high_correlation_pairs']} account pairs above warning threshold")
            if summary.get('critical_correlation_pairs', 0) > 0:
                report.append(f"• {summary['critical_correlation_pairs']} pairs at CRITICAL level")
            report.append("")
        
        return "\n".join(report)

    def _serialize_signal(self, signal) -> Dict[str, Any]:
        """Serialize original signal for logging."""
        return {
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "strength": signal.strength,
            "price": signal.price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit
        }

    def _serialize_decision(self, decision: AccountDecision) -> Dict[str, Any]:
        """Serialize account decision for logging."""
        return {
            "account_id": decision.account_id,
            "personality_id": decision.personality_id,
            "decision": decision.decision.value,
            "reasoning": decision.reasoning,
            "modifications": {
                "direction": decision.modifications.direction.value if decision.modifications.direction else None,
                "size": decision.modifications.size,
                "entry_price": decision.modifications.entry_price,
                "stop_loss": decision.modifications.stop_loss,
                "take_profit": decision.modifications.take_profit,
                "timing": decision.modifications.timing
            },
            "risk_assessment": {
                "personal_risk": decision.risk_assessment.personal_risk_level,
                "market_risk": decision.risk_assessment.market_risk_level,
                "portfolio_risk": decision.risk_assessment.portfolio_risk_level,
                "combined_risk": decision.risk_assessment.combined_risk_level,
                "risk_threshold": decision.risk_assessment.risk_threshold
            },
            "personality_factors": {
                "greed_factor": decision.personality_factors.greed_factor,
                "fear_factor": decision.personality_factors.fear_factor,
                "impatience_level": decision.personality_factors.impatience_level,
                "conformity_level": decision.personality_factors.conformity_level,
                "contrarian": decision.personality_factors.contrarian
            },
            "processed_at": decision.processed_at.isoformat(),
            "executed_at": decision.executed_at.isoformat() if decision.executed_at else None
        }

    def _serialize_metrics(self, metrics) -> Dict[str, Any]:
        """Serialize disagreement metrics for logging."""
        return {
            "participation_rate": metrics.participation_rate,
            "direction_consensus": metrics.direction_consensus,
            "timing_spread": metrics.timing_spread,
            "sizing_variation": metrics.sizing_variation,
            "profit_target_spread": metrics.profit_target_spread
        }

    def _serialize_correlation_impact(self, impact) -> Dict[str, Any]:
        """Serialize correlation impact for logging."""
        return {
            "before_signal": impact.before_signal,
            "after_signal": impact.after_signal,
            "adjustments": [
                {
                    "account_pair": adj.account_pair,
                    "before_correlation": adj.before_correlation,
                    "target_correlation": adj.target_correlation,
                    "adjustment_type": adj.adjustment_type,
                    "description": adj.adjustment_description
                }
                for adj in impact.target_adjustments
            ]
        }

    def _generate_human_summary(
        self,
        disagreement: SignalDisagreement,
        personalities: Dict[str, DisagreementProfile]
    ) -> str:
        """Generate human-readable summary of the disagreement."""
        
        signal = disagreement.original_signal
        decisions = disagreement.account_decisions
        metrics = disagreement.disagreement_metrics
        
        # Count decision types
        take_count = len([d for d in decisions if d.decision.value == 'take'])
        skip_count = len([d for d in decisions if d.decision.value == 'skip'])
        modify_count = len([d for d in decisions if d.decision.value == 'modify'])
        
        summary = f"Signal {signal.symbol} {signal.direction.value} at {signal.price}: "
        summary += f"{take_count} took, {skip_count} skipped, {modify_count} modified. "
        summary += f"Participation: {metrics.participation_rate:.1%}, "
        summary += f"Timing spread: {metrics.timing_spread:.0f}s"
        
        # Add notable patterns
        if skip_count > take_count:
            summary += " [High skip rate - possible risk aversion]"
        if metrics.timing_spread > 60:
            summary += " [Wide timing spread - coordination avoidance]"
        
        return summary

    def _write_jsonl_entry(self, file_path: Path, entry: Dict[str, Any]) -> None:
        """Write JSON Lines entry to log file."""
        try:
            with open(file_path, 'a') as f:
                f.write(json.dumps(entry, default=str) + '\n')
        except Exception as e:
            logger.error(f"Failed to write log entry to {file_path}: {e}")

    def _update_performance_metrics(self, disagreement: SignalDisagreement) -> None:
        """Update internal performance metrics."""
        self.performance_metrics["total_signals"] += 1
        self.performance_metrics["total_decisions"] += len(disagreement.account_decisions)
        
        for decision in disagreement.account_decisions:
            if decision.decision.value == 'skip':
                self.performance_metrics["skip_count"] += 1
                self.performance_metrics["disagreement_count"] += 1
            elif decision.decision.value == 'modify':
                self.performance_metrics["modify_count"] += 1
                self.performance_metrics["disagreement_count"] += 1

    def _load_recent_disagreements(self, cutoff: datetime) -> List[SignalDisagreement]:
        """Load recent disagreements from log files."""
        disagreements = []
        
        try:
            with open(self.disagreement_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_time >= cutoff:
                        # Convert back to SignalDisagreement object (simplified)
                        disagreements.append(self._deserialize_disagreement_entry(entry))
        except FileNotFoundError:
            logger.warning("No disagreement log file found")
        
        return disagreements

    def _deserialize_disagreement_entry(self, entry: Dict[str, Any]) -> SignalDisagreement:
        """Convert log entry back to SignalDisagreement object (simplified)."""
        # This is a simplified version for analysis purposes
        # In practice, you might want full deserialization
        
        from .models import SignalDisagreement, OriginalSignal, SignalDirection
        
        signal = OriginalSignal(
            symbol=entry['signal']['symbol'],
            direction=SignalDirection(entry['signal']['direction']),
            strength=entry['signal']['strength'],
            price=entry['signal']['price'],
            stop_loss=entry['signal']['stop_loss'],
            take_profit=entry['signal']['take_profit']
        )
        
        # Simplified disagreement object for analysis
        disagreement = SignalDisagreement(
            signal_id=entry['signal_id'],
            original_signal=signal,
            account_decisions=[],  # Would deserialize decisions if needed
            disagreement_metrics=None,  # Would deserialize metrics if needed
            correlation_impact=None
        )
        
        # Store raw entry for analysis
        disagreement._raw_entry = entry
        
        return disagreement

    def _calculate_summary_statistics(
        self,
        disagreements: List[SignalDisagreement],
        period_hours: int
    ) -> Dict[str, Any]:
        """Calculate summary statistics from disagreements."""
        
        if not disagreements:
            return {
                "total_signals": 0,
                "disagreement_rate": 0.0,
                "avg_participation_rate": 0.0,
                "correlation_alerts": 0,
                "take_decisions": 0,
                "skip_decisions": 0,
                "modify_decisions": 0,
                "take_rate": 0.0,
                "skip_rate": 0.0,
                "modify_rate": 0.0
            }
        
        total_signals = len(disagreements)
        total_decisions = 0
        disagreement_count = 0
        take_count = 0
        skip_count = 0
        modify_count = 0
        participation_rates = []
        
        for disagreement in disagreements:
            if hasattr(disagreement, '_raw_entry'):
                entry = disagreement._raw_entry
                decisions = entry['decisions']
                
                total_decisions += len(decisions)
                participation_rates.append(entry['metrics']['participation_rate'])
                
                for decision in decisions:
                    if decision['decision'] == 'take':
                        take_count += 1
                    elif decision['decision'] == 'skip':
                        skip_count += 1
                        disagreement_count += 1
                    elif decision['decision'] == 'modify':
                        modify_count += 1
                        disagreement_count += 1
        
        return {
            "total_signals": total_signals,
            "total_decisions": total_decisions,
            "disagreement_count": disagreement_count,
            "disagreement_rate": disagreement_count / total_decisions if total_decisions > 0 else 0.0,
            "avg_participation_rate": sum(participation_rates) / len(participation_rates) if participation_rates else 0.0,
            "take_decisions": take_count,
            "skip_decisions": skip_count,
            "modify_decisions": modify_count,
            "take_rate": take_count / total_decisions if total_decisions > 0 else 0.0,
            "skip_rate": skip_count / total_decisions if total_decisions > 0 else 0.0,
            "modify_rate": modify_count / total_decisions if total_decisions > 0 else 0.0,
            "correlation_alerts": self.performance_metrics.get("correlation_alerts", 0)
        }

    def _generate_detailed_analysis(self, disagreements: List[SignalDisagreement]) -> Dict[str, Any]:
        """Generate detailed analysis of disagreement patterns."""
        # Placeholder for detailed analysis
        return {
            "pattern_analysis": "Analysis would include timing patterns, decision clustering, etc.",
            "risk_factor_analysis": "Analysis of risk factors leading to disagreements",
            "personality_impact": "Analysis of personality factor influence on decisions"
        }

    def _analyze_account_decisions(self, decisions: List[Dict], account_id: str) -> Dict[str, Any]:
        """Analyze decisions for a specific account."""
        # Placeholder for account-specific analysis
        return {
            "account_id": account_id,
            "decision_count": len(decisions),
            "disagreement_patterns": "Analysis of account-specific patterns"
        }

    def _analyze_system_performance(self, disagreements: List[SignalDisagreement]) -> Dict[str, Any]:
        """Analyze overall system performance."""
        # Placeholder for system-wide analysis
        return {
            "system_performance": "Overall disagreement system performance analysis",
            "correlation_effectiveness": "Analysis of correlation reduction effectiveness"
        }