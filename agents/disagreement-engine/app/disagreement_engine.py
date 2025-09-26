"""
Main Disagreement Engine implementation.
Generates 15-20% disagreement rate across accounts to avoid correlation.
"""
import logging
import hashlib
from typing import List, Dict, Tuple
from datetime import datetime
import numpy as np

from .models import (
    SignalDisagreement, AccountDecision, OriginalSignal, DecisionType,
    DisagreementMetrics, CorrelationImpact, DisagreementProfile,
    RiskAssessment, PersonalityFactors, SignalModifications,
    CorrelationAdjustment
)
from .correlation_monitor import CorrelationMonitor
from .risk_assessment import RiskAssessmentEngine
from .decision_generator import DecisionGenerator

logger = logging.getLogger(__name__)


class DisagreementEngine:
    """
    Main engine for generating signal disagreements across trading accounts.
    
    Implements AC1: 15-20% of signals result in different actions across accounts
    """
    
    def __init__(
        self,
        correlation_monitor: CorrelationMonitor,
        risk_engine: RiskAssessmentEngine,
        decision_generator: DecisionGenerator
    ):
        self.correlation_monitor = correlation_monitor
        self.risk_engine = risk_engine  
        self.decision_generator = decision_generator
        
        # Core configuration
        self.target_disagreement_rate = (0.15, 0.20)  # 15-20%
        self.target_participation_rate = (0.80, 0.85)  # 80-85% should participate
        self.correlation_window = 100  # Last 100 trades for correlation
        
        logger.info(f"DisagreementEngine initialized with {self.target_disagreement_rate[0]*100:.0f}-{self.target_disagreement_rate[1]*100:.0f}% disagreement rate")

    def generate_disagreements(
        self, 
        signal: OriginalSignal, 
        accounts: List[Dict],
        personalities: Dict[str, DisagreementProfile],
        signal_id: str
    ) -> SignalDisagreement:
        """
        Generate disagreements for a signal across all accounts.
        
        Args:
            signal: Original trading signal
            accounts: List of account configurations
            personalities: Mapping of personality_id -> DisagreementProfile
            signal_id: Unique identifier for this signal
            
        Returns:
            Complete disagreement analysis
        """
        logger.info(f"Processing signal {signal_id} for {len(accounts)} accounts")
        
        # Step 1: Calculate base participation (80-85% should participate)
        participation_rate = self._calculate_participation_rate(signal, accounts, personalities)
        participating_accounts = self._select_participants(accounts, participation_rate)
        
        logger.info(f"Participation rate: {participation_rate:.2f} ({len(participating_accounts)}/{len(accounts)} accounts)")
        
        # Step 2: Generate decisions for all accounts
        decisions = []
        
        # Generate decisions for participants
        for account in participating_accounts:
            personality = personalities.get(account['personality_id'])
            if not personality:
                logger.warning(f"No personality found for account {account['id']}, using default")
                personality = self._get_default_personality(account['personality_id'])
                
            decision = self.decision_generator.generate_account_decision(
                signal, account, personality
            )
            decisions.append(decision)
        
        # Generate skip decisions for non-participants
        for account in accounts:
            if account not in participating_accounts:
                skip_decision = self.decision_generator.generate_skip_decision(
                    signal, account, personalities.get(account['personality_id'])
                )
                decisions.append(skip_decision)
        
        # Step 3: Adjust for correlation constraints
        decisions = self._adjust_for_correlation(decisions, signal)
        
        # Step 4: Calculate disagreement metrics
        metrics = self._calculate_disagreement_metrics(decisions, signal)
        
        # Step 5: Analyze correlation impact
        correlation_impact = self._analyze_correlation_impact(decisions, signal_id)
        
        # Create complete disagreement record
        disagreement = SignalDisagreement(
            signal_id=signal_id,
            original_signal=signal,
            account_decisions=decisions,
            disagreement_metrics=metrics,
            correlation_impact=correlation_impact
        )
        
        logger.info(f"Generated disagreements: {metrics.participation_rate:.1%} participation, "
                   f"{len([d for d in decisions if d.decision != DecisionType.TAKE])}/{len(decisions)} disagreements")
        
        return disagreement

    def _calculate_participation_rate(
        self, 
        signal: OriginalSignal, 
        accounts: List[Dict],
        personalities: Dict[str, DisagreementProfile]
    ) -> float:
        """Calculate what percentage of accounts should participate in this signal."""
        # Deterministic participation rate based on signal properties
        signal_hash = hashlib.md5(f"{signal.signal_id}{signal.timestamp}".encode()).hexdigest()
        rate_factor = (int(signal_hash[:8], 16) % 100) / 100.0
        min_rate, max_rate = self.target_participation_rate
        base_rate = min_rate + (max_rate - min_rate) * rate_factor
        
        # Adjust based on signal strength
        strength_adjustment = (signal.strength - 0.5) * 0.1  # ±5% adjustment
        
        # Adjust based on market conditions (placeholder)
        market_adjustment = 0.0  # Could be expanded with volatility data
        
        final_rate = max(0.6, min(0.95, base_rate + strength_adjustment + market_adjustment))
        
        logger.debug(f"Participation rate: {base_rate:.2f} + {strength_adjustment:.2f} + {market_adjustment:.2f} = {final_rate:.2f}")
        
        return final_rate

    def _select_participants(self, accounts: List[Dict], participation_rate: float) -> List[Dict]:
        """Select which accounts will participate in the signal."""
        target_count = int(len(accounts) * participation_rate)
        
        # Deterministically select participants based on signal and accounts
        # Sort accounts by a hash of their ID and the signal to get deterministic ordering
        sorted_accounts = sorted(
            accounts,
            key=lambda acc: hashlib.md5(f"{acc}{signal.signal_id}".encode()).hexdigest()
        )
        participants = sorted_accounts[:min(target_count, len(accounts))]
        
        return participants

    def _adjust_for_correlation(
        self, 
        decisions: List[AccountDecision], 
        signal: OriginalSignal
    ) -> List[AccountDecision]:
        """
        Adjust decisions to maintain correlation below 0.7 threshold.
        
        This is critical for avoiding prop firm detection.
        """
        logger.debug("Adjusting decisions for correlation constraints")
        
        # Get current correlation levels
        current_correlations = self.correlation_monitor.get_current_correlations()
        
        # Identify high-correlation pairs
        high_correlation_pairs = [
            (pair, corr) for pair, corr in current_correlations.items() 
            if corr > 0.65  # Start adjusting before hitting 0.7 threshold
        ]
        
        if not high_correlation_pairs:
            logger.debug("No high correlation pairs found, no adjustment needed")
            return decisions
        
        logger.info(f"Found {len(high_correlation_pairs)} high-correlation pairs, forcing disagreements")
        
        # Force disagreements for high-correlation pairs
        adjustments_made = []
        
        for pair, correlation in high_correlation_pairs:
            account1_id, account2_id = pair.split('_')
            
            # Find decisions for this pair
            decision1 = next((d for d in decisions if d.account_id == account1_id), None)
            decision2 = next((d for d in decisions if d.account_id == account2_id), None)
            
            if not decision1 or not decision2:
                continue
                
            # Force disagreement if both are taking the same action
            if decision1.decision == decision2.decision == DecisionType.TAKE:
                # Deterministically choose one to modify based on account IDs
                hash_val = hashlib.md5(f"{acc1}{acc2}".encode()).hexdigest()
                modify_first = int(hash_val[:2], 16) % 2 == 0
                if modify_first:
                    decision1.decision = DecisionType.SKIP
                    decision1.reasoning = "Avoiding correlation with related account"
                    logger.debug(f"Forced {account1_id} to skip to reduce correlation with {account2_id}")
                else:
                    # Modify decision2 significantly
                    decision2.decision = DecisionType.MODIFY
                    # Deterministic TP modification based on accounts
                    tp_hash = hashlib.md5(f"{account2_id}{signal.signal_id}tp".encode()).hexdigest()
                    tp_factor = 0.7 + (int(tp_hash[:4], 16) % 600) / 1000.0  # 0.7 to 1.3
                    decision2.modifications.take_profit = signal.take_profit * tp_factor
                    decision2.reasoning = "Personal profit target preference"
                    logger.debug(f"Forced {account2_id} to modify TP to reduce correlation with {account1_id}")
                
                adjustments_made.append(
                    CorrelationAdjustment(
                        account_pair=pair,
                        before_correlation=correlation,
                        target_correlation=0.6,  # Target to get well below 0.7
                        adjustment_type="forced_disagreement",
                        adjustment_description=f"Forced disagreement between {account1_id} and {account2_id}"
                    )
                )
        
        if adjustments_made:
            logger.info(f"Made {len(adjustments_made)} correlation adjustments")
        
        return decisions

    def _calculate_disagreement_metrics(
        self, 
        decisions: List[AccountDecision], 
        signal: OriginalSignal
    ) -> DisagreementMetrics:
        """Calculate metrics about the disagreement distribution."""
        if not decisions:
            return DisagreementMetrics(
                participation_rate=0.0,
                direction_consensus=0.0,
                timing_spread=0.0,
                sizing_variation=0.0,
                profit_target_spread=0.0
            )
        
        # Participation rate
        takers = [d for d in decisions if d.decision in [DecisionType.TAKE, DecisionType.MODIFY]]
        participation_rate = len(takers) / len(decisions)
        
        # Direction consensus (among participants)
        if takers:
            long_count = sum(1 for d in takers 
                           if (d.modifications.direction or signal.direction).value == 'long')
            direction_consensus = max(long_count, len(takers) - long_count) / len(takers)
        else:
            direction_consensus = 0.0
        
        # Timing spread (among participants with timing modifications)
        timings = [d.modifications.timing for d in takers if d.modifications.timing is not None]
        timing_spread = max(timings) - min(timings) if timings else 0.0
        
        # Sizing variation (coefficient of variation)
        sizes = [d.modifications.size for d in takers if d.modifications.size is not None]
        if len(sizes) > 1:
            sizing_variation = np.std(sizes) / np.mean(sizes)
        else:
            sizing_variation = 0.0
        
        # Profit target spread
        profit_targets = []
        for d in takers:
            tp = d.modifications.take_profit if d.modifications.take_profit else signal.take_profit
            profit_targets.append(tp)
        
        profit_target_spread = max(profit_targets) - min(profit_targets) if profit_targets else 0.0
        
        return DisagreementMetrics(
            participation_rate=participation_rate,
            direction_consensus=direction_consensus,
            timing_spread=timing_spread,
            sizing_variation=sizing_variation,
            profit_target_spread=profit_target_spread
        )

    def _analyze_correlation_impact(
        self, 
        decisions: List[AccountDecision], 
        signal_id: str
    ) -> CorrelationImpact:
        """Analyze how this signal will impact account correlations."""
        # Get correlations before this signal
        before_correlations = self.correlation_monitor.get_current_correlations().copy()
        
        # Simulate correlations after this signal
        # In real implementation, this would use actual trade outcomes
        after_correlations = self._simulate_correlation_impact(decisions, before_correlations)
        
        return CorrelationImpact(
            before_signal=before_correlations,
            after_signal=after_correlations,
            target_adjustments=[]  # Would be populated with adjustment strategies
        )

    def _simulate_correlation_impact(
        self, 
        decisions: List[AccountDecision], 
        current_correlations: Dict[str, float]
    ) -> Dict[str, float]:
        """Simulate how decisions will impact correlations."""
        # Simple simulation - in reality this would be more sophisticated
        simulated = current_correlations.copy()
        
        # Find account pairs that made the same decision
        decision_groups = {}
        for decision in decisions:
            key = f"{decision.decision.value}_{decision.modifications.take_profit or 'default'}"
            if key not in decision_groups:
                decision_groups[key] = []
            decision_groups[key].append(decision.account_id)
        
        # Adjust correlations based on decision similarity
        for group_accounts in decision_groups.values():
            if len(group_accounts) > 1:
                # Accounts making similar decisions will have slightly higher correlation
                for i, account1 in enumerate(group_accounts):
                    for account2 in group_accounts[i+1:]:
                        pair_key = f"{account1}_{account2}"
                        reverse_key = f"{account2}_{account1}"
                        
                        if pair_key in simulated:
                            simulated[pair_key] = min(0.95, simulated[pair_key] + 0.02)
                        elif reverse_key in simulated:
                            simulated[reverse_key] = min(0.95, simulated[reverse_key] + 0.02)
        
        return simulated

    def _get_default_personality(self, personality_id: str) -> DisagreementProfile:
        """Create a default disagreement profile for missing personalities."""
        from .models import DecisionBiases, SituationalModifiers, CorrelationAwareness
        
        return DisagreementProfile(
            personality_id=personality_id,
            base_disagreement_rate=0.175,  # Middle of 15-20% range
            biases=DecisionBiases(
                risk_aversion=0.5,
                signal_skepticism=0.3,
                crowd_following=0.4,
                profit_taking=0.5,
                loss_avoidance=0.5
            ),
            situational_modifiers=SituationalModifiers(
                market_volatility=0.2,
                news_events=0.1,
                time_of_day={},
                day_of_week={}
            ),
            correlation_awareness=CorrelationAwareness(
                monitor_correlation=True,
                correlation_sensitivity=0.3,
                anti_correlation_bias=0.2
            )
        )

    def validate_disagreement_rate(self, recent_signals: List[SignalDisagreement]) -> Dict[str, float]:
        """
        Validate that disagreement rates are within target range.
        
        Returns metrics for monitoring and adjustment.
        """
        if not recent_signals:
            return {"disagreement_rate": 0.0, "target_min": 0.15, "target_max": 0.20, "in_range": False}
        
        total_decisions = 0
        total_disagreements = 0
        
        for signal in recent_signals:
            decisions = signal.account_decisions
            total_decisions += len(decisions)
            
            # Count disagreements (any decision that's not a straight "take")
            disagreements = len([d for d in decisions if d.decision != DecisionType.TAKE])
            total_disagreements += disagreements
        
        disagreement_rate = total_disagreements / total_decisions if total_decisions > 0 else 0.0
        in_range = self.target_disagreement_rate[0] <= disagreement_rate <= self.target_disagreement_rate[1]
        
        return {
            "disagreement_rate": disagreement_rate,
            "target_min": self.target_disagreement_rate[0],
            "target_max": self.target_disagreement_rate[1],
            "in_range": in_range,
            "total_signals": len(recent_signals),
            "total_decisions": total_decisions,
            "total_disagreements": total_disagreements
        }