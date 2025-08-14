"""
Adaptive Risk Parameter Tuner

Main orchestrator for the parameter optimization system that coordinates
all optimizers and applies safety constraints.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import json

from .models import (
    OptimizationAnalysis, OptimizationStatus, ParameterAdjustment, 
    ParameterChangeLog, ImplementationMethod, RiskParameterSet,
    generate_id
)
from .performance_calculator import TradeRecord, RollingPerformanceCalculator
from .position_sizing_optimizer import PositionSizingOptimizer
from .stop_loss_optimizer import StopLossOptimizer, ATRData
from .take_profit_optimizer import TakeProfitOptimizer
from .signal_confidence_optimizer import SignalConfidenceOptimizer
from .parameter_constraints import ParameterConstraints

logger = logging.getLogger(__name__)


class AdaptiveRiskParameterTuner:
    """
    Main coordinator for adaptive risk parameter optimization
    """
    
    def __init__(self, storage_path: str = "./parameter_optimization"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.performance_calculator = RollingPerformanceCalculator()
        self.position_optimizer = PositionSizingOptimizer()
        self.stop_loss_optimizer = StopLossOptimizer()
        self.take_profit_optimizer = TakeProfitOptimizer()
        self.signal_optimizer = SignalConfidenceOptimizer()
        self.constraints = ParameterConstraints(str(self.storage_path / "constraints"))
        
        # Configuration
        self.auto_approval_enabled = True
        self.min_confidence_for_auto = 0.8
        self.optimization_frequency_days = 7  # Weekly optimization
        
        # Storage
        self.optimizations: Dict[str, OptimizationAnalysis] = {}
        self.parameter_sets: Dict[str, RiskParameterSet] = {}
        self.change_logs: Dict[str, ParameterChangeLog] = {}
        
        self._load_existing_data()
    
    def optimize_account_parameters(self, account_id: str,
                                   trade_history: List[TradeRecord],
                                   market_data: Optional[List[ATRData]] = None,
                                   force_optimization: bool = False) -> OptimizationAnalysis:
        """
        Perform comprehensive parameter optimization for an account
        
        Args:
            account_id: Account identifier
            trade_history: Historical trade records
            market_data: Market data for volatility analysis
            force_optimization: Force optimization even if recent one exists
            
        Returns:
            Optimization analysis results
        """
        try:
            logger.info(f"Starting parameter optimization for account {account_id}")
            
            # Check if recent optimization exists
            if not force_optimization and self._has_recent_optimization(account_id):
                logger.info(f"Recent optimization exists for {account_id}, skipping")
                return self._get_latest_optimization(account_id)
            
            # Get current parameters
            current_params = self._get_current_parameters(account_id)
            
            # Calculate current performance
            current_performance = self.performance_calculator.calculate_current_performance(
                account_id, trade_history
            )
            
            # Create optimization analysis
            optimization = OptimizationAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                current_performance=current_performance,
                status=OptimizationStatus.IN_PROGRESS
            )
            
            # Set analysis period
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            optimization.analysis_period = {
                "start": start_date,
                "end": end_date,
                "trade_count": len(trade_history),
                "market_regimes": list(set([t.market_regime.value for t in trade_history]))
            }
            
            # Run individual optimizers
            adjustments = []
            
            # Position sizing optimization
            pos_adjustment = self.position_optimizer.optimize_position_sizing(
                account_id, current_params.position_sizing, current_performance, trade_history
            )
            if pos_adjustment:
                adjustments.append(pos_adjustment)
            
            # Stop loss optimization
            if market_data:
                # Use first symbol from trade history
                symbols = list(set([t.symbol for t in trade_history]))
                for symbol in symbols[:1]:  # Optimize for primary symbol
                    sl_adjustment = self.stop_loss_optimizer.optimize_stop_loss(
                        account_id, symbol, current_params.stop_loss, 
                        [t for t in trade_history if t.symbol == symbol], market_data
                    )
                    if sl_adjustment:
                        adjustments.append(sl_adjustment)
                        break
            
            # Take profit optimization
            tp_adjustment = self.take_profit_optimizer.optimize_take_profit(
                account_id, current_params.take_profit, trade_history
            )
            if tp_adjustment:
                adjustments.append(tp_adjustment)
            
            # Signal confidence optimization
            sig_adjustment = self.signal_optimizer.optimize_signal_confidence(
                account_id, current_params.signal_filtering, trade_history
            )
            if sig_adjustment:
                adjustments.append(sig_adjustment)
            
            # Apply constraints to all adjustments
            validated_adjustments = []
            for adjustment in adjustments:
                is_valid, violations = self.constraints.validate_adjustment(account_id, adjustment)
                if is_valid:
                    validated_adjustments.append(adjustment)
                else:
                    logger.warning(f"Adjustment rejected for {account_id}: {violations}")
            
            optimization.adjustments = validated_adjustments
            
            # Create implementation plan
            if validated_adjustments:
                optimization.implementation = self._create_implementation_plan(
                    account_id, validated_adjustments
                )
                optimization.status = OptimizationStatus.COMPLETED
            else:
                optimization.status = OptimizationStatus.COMPLETED
                logger.info(f"No valid adjustments found for {account_id}")
            
            # Store optimization
            self.optimizations[optimization.analysis_id] = optimization
            self._save_optimization(optimization)
            
            # Auto-approve if enabled
            if self.auto_approval_enabled and validated_adjustments:
                self._auto_approve_adjustments(account_id, optimization)
            
            logger.info(f"Parameter optimization completed for {account_id}: {len(validated_adjustments)} adjustments")
            return optimization
            
        except Exception as e:
            logger.error(f"Parameter optimization failed for {account_id}: {e}")
            
            # Return failed optimization
            failed_optimization = OptimizationAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                status=OptimizationStatus.FAILED
            )
            return failed_optimization
    
    def implement_adjustments(self, account_id: str, optimization_id: str,
                            approved_adjustment_ids: List[str],
                            implementation_method: ImplementationMethod = ImplementationMethod.IMMEDIATE) -> ParameterChangeLog:
        """
        Implement approved parameter adjustments
        
        Args:
            account_id: Account identifier
            optimization_id: Optimization analysis ID
            approved_adjustment_ids: List of approved adjustment IDs
            implementation_method: How to implement the changes
            
        Returns:
            Parameter change log
        """
        try:
            optimization = self.optimizations.get(optimization_id)
            if not optimization:
                raise ValueError(f"Optimization not found: {optimization_id}")
            
            # Get approved adjustments
            approved_adjustments = [
                adj for adj in optimization.adjustments
                if adj.adjustment_id in approved_adjustment_ids
            ]
            
            if not approved_adjustments:
                raise ValueError("No approved adjustments found")
            
            # Create change log
            change_log = ParameterChangeLog(
                change_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                parameter_changes=approved_adjustments,
                implementation_method=implementation_method,
                authorized_by="system"
            )
            
            # Create rollback conditions
            for adjustment in approved_adjustments:
                rollback_conditions = self.constraints.create_rollback_conditions(adjustment)
                change_log.monitoring["rollback_triggers"].extend(rollback_conditions)
            
            # Apply changes based on implementation method
            if implementation_method == ImplementationMethod.IMMEDIATE:
                self._apply_immediate_changes(account_id, approved_adjustments)
            elif implementation_method == ImplementationMethod.GRADUAL:
                self._apply_gradual_changes(account_id, approved_adjustments)
            elif implementation_method == ImplementationMethod.AB_TEST:
                self._apply_ab_test_changes(account_id, approved_adjustments)
            
            # Record changes for constraint tracking
            for adjustment in approved_adjustments:
                self.constraints.record_adjustment(account_id, adjustment)
                adjustment.implementation["approved"] = True
                adjustment.implementation["implemented_at"] = datetime.utcnow()
            
            # Store change log
            self.change_logs[change_log.change_id] = change_log
            self._save_change_log(change_log)
            
            logger.info(f"Implemented {len(approved_adjustments)} parameter changes for {account_id}")
            return change_log
            
        except Exception as e:
            logger.error(f"Failed to implement adjustments for {account_id}: {e}")
            raise
    
    def monitor_parameter_changes(self, account_id: str, change_id: str,
                                current_performance: Any) -> Dict[str, Any]:
        """
        Monitor the impact of parameter changes
        
        Args:
            account_id: Account identifier
            change_id: Parameter change ID
            current_performance: Current performance metrics
            
        Returns:
            Monitoring results and recommendations
        """
        try:
            change_log = self.change_logs.get(change_id)
            if not change_log:
                raise ValueError(f"Change log not found: {change_id}")
            
            monitoring_results = {
                "change_id": change_id,
                "account_id": account_id,
                "monitoring_period_days": change_log.monitoring.get("monitoring_period", 7),
                "rollback_recommended": False,
                "performance_impact": {},
                "risk_assessment": {},
                "recommendations": []
            }
            
            # Check rollback conditions
            rollback_triggered = self._check_rollback_conditions(change_log, current_performance)
            if rollback_triggered:
                monitoring_results["rollback_recommended"] = True
                monitoring_results["recommendations"].append("Immediate rollback recommended due to triggered conditions")
            
            # Performance impact analysis (simplified)
            if change_log.performance_tracking.get("pre_change_metrics"):
                pre_metrics = change_log.performance_tracking["pre_change_metrics"]
                
                # Compare key metrics (simplified)
                performance_delta = {
                    "sharpe_ratio_change": getattr(current_performance, "sharpe_ratio", 0) - getattr(pre_metrics, "sharpe_ratio", 0),
                    "max_drawdown_change": getattr(current_performance, "max_drawdown", 0) - getattr(pre_metrics, "max_drawdown", 0),
                    "win_rate_change": getattr(current_performance, "win_rate", 0) - getattr(pre_metrics, "win_rate", 0)
                }
                
                monitoring_results["performance_impact"] = performance_delta
                
                # Generate recommendations
                if performance_delta["sharpe_ratio_change"] < -0.2:
                    monitoring_results["recommendations"].append("Sharpe ratio has declined significantly")
                if performance_delta["max_drawdown_change"] > 0.05:
                    monitoring_results["recommendations"].append("Maximum drawdown has increased")
            
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Failed to monitor parameter changes for {account_id}: {e}")
            return {"error": str(e)}
    
    def get_optimization_report(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive optimization report for an account
        
        Args:
            account_id: Account identifier
            days: Number of days to include in report
            
        Returns:
            Comprehensive optimization report
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent optimizations
            account_optimizations = [
                opt for opt in self.optimizations.values()
                if opt.account_id == account_id and opt.timestamp >= cutoff_date
            ]
            
            # Get recent changes
            account_changes = [
                change for change in self.change_logs.values()
                if change.account_id == account_id and change.timestamp >= cutoff_date
            ]
            
            # Get constraint summary
            constraint_summary = self.constraints.get_constraint_summary(account_id)
            
            # Current parameters
            current_params = self._get_current_parameters(account_id)
            
            report = {
                "account_id": account_id,
                "report_period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "optimizations_count": len(account_optimizations),
                    "parameter_changes_count": len(account_changes),
                    "current_parameter_set_version": getattr(current_params, "version", "unknown")
                },
                "optimizations": [
                    {
                        "analysis_id": opt.analysis_id,
                        "timestamp": opt.timestamp.isoformat(),
                        "status": opt.status.value,
                        "adjustments_count": len(opt.adjustments),
                        "adjustments": [
                            {
                                "parameter": adj.parameter_name,
                                "category": adj.category.value,
                                "current_value": adj.current_value,
                                "proposed_value": adj.proposed_value,
                                "change_percentage": adj.change_percentage,
                                "approved": adj.implementation.get("approved", False)
                            }
                            for adj in opt.adjustments
                        ]
                    }
                    for opt in account_optimizations
                ],
                "parameter_changes": [
                    {
                        "change_id": change.change_id,
                        "timestamp": change.timestamp.isoformat(),
                        "implementation_method": change.implementation_method.value,
                        "changes_count": len(change.parameter_changes),
                        "authorized_by": change.authorized_by
                    }
                    for change in account_changes
                ],
                "constraints": constraint_summary,
                "current_parameters": {
                    "position_sizing": dict(current_params.position_sizing),
                    "stop_loss": dict(current_params.stop_loss),
                    "take_profit": dict(current_params.take_profit),
                    "signal_filtering": dict(current_params.signal_filtering)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate optimization report for {account_id}: {e}")
            return {"error": str(e)}
    
    def _has_recent_optimization(self, account_id: str) -> bool:
        """Check if account has recent optimization"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.optimization_frequency_days)
        
        for optimization in self.optimizations.values():
            if (optimization.account_id == account_id and 
                optimization.timestamp >= cutoff_date and
                optimization.status == OptimizationStatus.COMPLETED):
                return True
        
        return False
    
    def _get_latest_optimization(self, account_id: str) -> OptimizationAnalysis:
        """Get latest optimization for account"""
        account_optimizations = [
            opt for opt in self.optimizations.values()
            if opt.account_id == account_id
        ]
        
        if account_optimizations:
            return max(account_optimizations, key=lambda x: x.timestamp)
        else:
            # Return empty optimization
            return OptimizationAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                status=OptimizationStatus.PENDING
            )
    
    def _get_current_parameters(self, account_id: str) -> RiskParameterSet:
        """Get current parameter set for account"""
        # Try to get from storage first
        if account_id in self.parameter_sets:
            return self.parameter_sets[account_id]
        
        # Create default parameter set
        default_params = RiskParameterSet(
            id=generate_id(),
            version="1.0",
            account_id=account_id,
            effective_date=datetime.utcnow()
        )
        
        self.parameter_sets[account_id] = default_params
        return default_params
    
    def _create_implementation_plan(self, account_id: str, 
                                  adjustments: List[ParameterAdjustment]) -> Dict[str, Any]:
        """Create implementation plan for adjustments"""
        plan = {
            "implementation_date": datetime.utcnow(),
            "gradual_rollout": False,
            "rollout_percentage": 100.0,
            "monitoring_period": 7  # Days
        }
        
        # Check if any adjustment requires gradual rollout
        for adjustment in adjustments:
            if abs(adjustment.change_percentage) > 0.2:  # Large change
                plan["gradual_rollout"] = True
                plan["rollout_percentage"] = 50.0  # Start with 50%
                plan["monitoring_period"] = 14  # Longer monitoring
                break
        
        return plan
    
    def _auto_approve_adjustments(self, account_id: str, optimization: OptimizationAnalysis):
        """Auto-approve adjustments if they meet criteria"""
        try:
            auto_approved = []
            
            for adjustment in optimization.adjustments:
                confidence = adjustment.analysis.get("confidence_level", 0.0)
                change_magnitude = abs(adjustment.change_percentage)
                
                # Auto-approve if high confidence and reasonable change
                if (confidence >= self.min_confidence_for_auto and 
                    change_magnitude <= 0.15):  # Max 15% change for auto-approval
                    
                    auto_approved.append(adjustment.adjustment_id)
            
            if auto_approved:
                self.implement_adjustments(
                    account_id, optimization.analysis_id, auto_approved,
                    ImplementationMethod.GRADUAL
                )
                logger.info(f"Auto-approved {len(auto_approved)} adjustments for {account_id}")
            
        except Exception as e:
            logger.warning(f"Auto-approval failed for {account_id}: {e}")
    
    def _apply_immediate_changes(self, account_id: str, adjustments: List[ParameterAdjustment]):
        """Apply parameter changes immediately"""
        current_params = self._get_current_parameters(account_id)
        
        for adjustment in adjustments:
            self._update_parameter_value(current_params, adjustment)
        
        # Update version and effective date
        current_params.version = f"{float(current_params.version) + 0.1:.1f}"
        current_params.effective_date = datetime.utcnow()
        
        # Save updated parameters
        self._save_parameter_set(current_params)
    
    def _apply_gradual_changes(self, account_id: str, adjustments: List[ParameterAdjustment]):
        """Apply parameter changes gradually"""
        # For now, implement same as immediate but could add scheduling
        self._apply_immediate_changes(account_id, adjustments)
    
    def _apply_ab_test_changes(self, account_id: str, adjustments: List[ParameterAdjustment]):
        """Apply parameter changes via A/B testing"""
        # For now, implement same as immediate but could add A/B test logic
        self._apply_immediate_changes(account_id, adjustments)
    
    def _update_parameter_value(self, params: RiskParameterSet, adjustment: ParameterAdjustment):
        """Update a specific parameter value"""
        param_name = adjustment.parameter_name
        new_value = adjustment.proposed_value
        category = adjustment.category
        
        if category.value == "position_sizing":
            params.position_sizing[param_name] = new_value
        elif category.value == "stop_loss":
            params.stop_loss[param_name] = new_value
        elif category.value == "take_profit":
            params.take_profit[param_name] = new_value
        elif category.value == "signal_filtering":
            params.signal_filtering[param_name] = new_value
    
    def _check_rollback_conditions(self, change_log: ParameterChangeLog, 
                                 current_performance: Any) -> bool:
        """Check if any rollback conditions are triggered"""
        # Simplified rollback checking
        # In practice, this would evaluate each rollback condition
        
        rollback_triggers = change_log.monitoring.get("rollback_triggers", [])
        
        for condition in rollback_triggers:
            # Simplified condition checking
            if condition.condition_type == "performance_degradation":
                # Check if performance has degraded significantly
                pre_metrics = change_log.performance_tracking.get("pre_change_metrics")
                if pre_metrics:
                    current_sharpe = getattr(current_performance, "sharpe_ratio", 0)
                    pre_sharpe = getattr(pre_metrics, "sharpe_ratio", 0)
                    
                    if current_sharpe < pre_sharpe * (1 - condition.threshold):
                        return True
        
        return False
    
    def _load_existing_data(self):
        """Load existing optimizations and parameter sets"""
        try:
            # Load optimizations
            opt_file = self.storage_path / "optimizations.json"
            if opt_file.exists():
                # Implementation would load from JSON
                pass
            
            # Load parameter sets
            params_file = self.storage_path / "parameter_sets.json"
            if params_file.exists():
                # Implementation would load from JSON
                pass
            
            # Load change logs
            changes_file = self.storage_path / "change_logs.json"
            if changes_file.exists():
                # Implementation would load from JSON
                pass
            
        except Exception as e:
            logger.warning(f"Failed to load existing data: {e}")
    
    def _save_optimization(self, optimization: OptimizationAnalysis):
        """Save optimization to storage"""
        # Implementation would save to JSON/database
        pass
    
    def _save_parameter_set(self, params: RiskParameterSet):
        """Save parameter set to storage"""
        # Implementation would save to JSON/database
        pass
    
    def _save_change_log(self, change_log: ParameterChangeLog):
        """Save change log to storage"""
        # Implementation would save to JSON/database
        pass