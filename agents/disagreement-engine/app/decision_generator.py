"""
Decision Generator - Creates individual account decisions based on personality.
"""
import random
import logging
from typing import Dict, Optional
from datetime import datetime

from .models import (
    AccountDecision, OriginalSignal, DecisionType, DisagreementProfile,
    RiskAssessment, PersonalityFactors, SignalModifications
)
from .risk_assessment import RiskAssessmentEngine

logger = logging.getLogger(__name__)


# Human-like decision reasoning templates
SKIP_REASONS = [
    "Market too volatile for my risk appetite",
    "Already have similar exposure", 
    "Waiting for better entry opportunity",
    "Not convinced by signal strength",
    "Taking a break after recent losses",
    "Prefer to trade different session",
    "Signal came during lunch break",
    "Weekend gap makes me cautious",
    "News event uncertainty",
    "Account approaching daily limit",
    "Risk management says pass on this one",
    "Pair correlation too high right now",
    "Technical setup doesn't look clean to me",
    "Economic calendar makes me nervous"
]

MODIFICATION_REASONS = [
    "Taking smaller position due to volatility",
    "Adjusting profit target based on support/resistance", 
    "Tighter stop loss for risk management",
    "Wider stop loss for volatility buffer",
    "Personal preference for this pair",
    "Account size adjustment",
    "End of week position sizing",
    "Conservative approach during news",
    "Scaling in gradually on this setup",
    "Modified TP based on daily range",
    "Adjusted for overnight risk",
    "Personal money management rules"
]


class DecisionGenerator:
    """
    Generates individual account decisions based on personality profiles.
    
    Handles personality-based modifications to signals including:
    - Risk-based skipping
    - Greed/fear factor adjustments
    - Timing preferences
    - Human-like reasoning
    """
    
    def __init__(self, risk_engine: RiskAssessmentEngine):
        self.risk_engine = risk_engine
        logger.info("DecisionGenerator initialized")

    def generate_account_decision(
        self,
        signal: OriginalSignal,
        account: Dict,
        personality: DisagreementProfile
    ) -> AccountDecision:
        """
        Generate a decision for a specific account based on personality.
        
        Args:
            signal: Original trading signal
            account: Account configuration dict
            personality: Personality profile for decision making
            
        Returns:
            Complete account decision with reasoning
        """
        account_id = account['id']
        logger.debug(f"Generating decision for account {account_id}")
        
        # Create base decision structure
        decision = AccountDecision(
            account_id=account_id,
            personality_id=personality.personality_id,
            decision=DecisionType.TAKE,  # Default to taking the signal
            reasoning="Following signal as presented",
            risk_assessment=RiskAssessment(
                personal_risk_level=0.0,
                market_risk_level=0.0, 
                portfolio_risk_level=0.0,
                combined_risk_level=0.0,
                risk_threshold=0.5
            ),
            personality_factors=self._extract_personality_factors(personality),
            modifications=SignalModifications()
        )
        
        # Step 1: Risk assessment
        risk_assessment = self.risk_engine.assess_risk(signal, account, personality)
        decision.risk_assessment = risk_assessment
        
        # Step 2: Check if risk exceeds personal threshold
        if risk_assessment.combined_risk_level > risk_assessment.risk_threshold:
            decision.decision = DecisionType.SKIP
            decision.reasoning = random.choice(SKIP_REASONS)
            logger.debug(f"Account {account_id} skipping due to risk: {risk_assessment.combined_risk_level:.2f} > {risk_assessment.risk_threshold:.2f}")
            return decision
        
        # Step 3: Apply personality-based modifications
        modifications = self._apply_personality_modifications(signal, personality, account)
        decision.modifications = modifications
        
        # Step 4: Determine if this is a modification or straight take
        if self._has_significant_modifications(modifications):
            decision.decision = DecisionType.MODIFY
            decision.reasoning = random.choice(MODIFICATION_REASONS)
            logger.debug(f"Account {account_id} modifying signal")
        else:
            decision.decision = DecisionType.TAKE
            decision.reasoning = "Signal looks good, taking as presented"
            logger.debug(f"Account {account_id} taking signal straight")
        
        # Step 5: Apply disagreement rate check
        if self._should_force_disagreement(personality):
            decision = self._force_disagreement(decision, signal)
            logger.debug(f"Account {account_id} forced disagreement due to base disagreement rate")
        
        return decision

    def generate_skip_decision(
        self,
        signal: OriginalSignal,
        account: Dict,
        personality: Optional[DisagreementProfile]
    ) -> AccountDecision:
        """Generate a skip decision for accounts not participating."""
        
        if not personality:
            personality = self._get_default_personality(account.get('personality_id', 'default'))
        
        return AccountDecision(
            account_id=account['id'],
            personality_id=personality.personality_id,
            decision=DecisionType.SKIP,
            reasoning=random.choice(SKIP_REASONS),
            risk_assessment=RiskAssessment(
                personal_risk_level=0.8,  # High risk assumed for skip
                market_risk_level=0.5,
                portfolio_risk_level=0.3,
                combined_risk_level=0.8,
                risk_threshold=0.7
            ),
            personality_factors=self._extract_personality_factors(personality),
            modifications=SignalModifications()
        )

    def _extract_personality_factors(self, personality: DisagreementProfile) -> PersonalityFactors:
        """Extract personality factors for decision record."""
        biases = personality.biases
        
        return PersonalityFactors(
            greed_factor=1.0 - biases.profit_taking,  # Higher profit_taking bias = lower greed
            fear_factor=biases.loss_avoidance,
            impatience_level=1.0 - biases.risk_aversion,  # Risk averse = more patient
            conformity_level=biases.crowd_following,
            contrarian=biases.crowd_following < 0.3  # Low crowd following = contrarian
        )

    def _apply_personality_modifications(
        self,
        signal: OriginalSignal,
        personality: DisagreementProfile,
        account: Dict
    ) -> SignalModifications:
        """Apply personality-based modifications to the signal."""
        modifications = SignalModifications()
        biases = personality.biases
        
        # 1. Greed factor affects take profit
        greed_factor = 1.0 - biases.profit_taking  # Convert profit_taking bias to greed
        tp_multiplier = 0.8 + (greed_factor * 0.4)  # Range: 0.8x to 1.2x
        modifications.take_profit = signal.take_profit * tp_multiplier
        
        # 2. Fear factor affects stop loss  
        fear_factor = biases.loss_avoidance
        sl_multiplier = 1.2 - (fear_factor * 0.4)  # Range: 0.8x to 1.2x (inverse)
        modifications.stop_loss = signal.stop_loss * sl_multiplier
        
        # 3. Impatience affects timing
        impatience = 1.0 - biases.risk_aversion  # Risk averse = more patient
        max_delay = 30 * (1 - impatience)  # 0 to 30 seconds
        if max_delay > 1:  # Only add timing if meaningful delay
            modifications.timing = random.uniform(0, max_delay)
        
        # 4. Position sizing based on risk aversion
        risk_aversion = biases.risk_aversion
        size_multiplier = 1.2 - (risk_aversion * 0.4)  # Range: 0.8x to 1.2x
        base_size = account.get('base_position_size', 0.01)
        modifications.size = base_size * size_multiplier
        
        # 5. Direction contrarian check
        if biases.crowd_following < 0.2 and random.random() < 0.1:  # 10% chance for strong contrarians
            modifications.direction = 'short' if signal.direction.value == 'long' else 'long'
        
        logger.debug(f"Applied modifications: TP={tp_multiplier:.2f}x, SL={sl_multiplier:.2f}x, "
                    f"size={size_multiplier:.2f}x, delay={modifications.timing or 0:.1f}s")
        
        return modifications

    def _has_significant_modifications(self, modifications: SignalModifications) -> bool:
        """Check if modifications are significant enough to count as 'modify' vs 'take'."""
        significant_changes = 0
        
        # Check take profit change > 10%
        if modifications.take_profit and abs(modifications.take_profit - 1.0) > 0.1:
            significant_changes += 1
            
        # Check stop loss change > 10%
        if modifications.stop_loss and abs(modifications.stop_loss - 1.0) > 0.1:
            significant_changes += 1
            
        # Check timing delay > 5 seconds
        if modifications.timing and modifications.timing > 5:
            significant_changes += 1
            
        # Check size change > 15%
        if modifications.size and abs(modifications.size - 1.0) > 0.15:
            significant_changes += 1
            
        # Check direction change
        if modifications.direction:
            significant_changes += 2  # Direction change is always significant
        
        return significant_changes >= 1

    def _should_force_disagreement(self, personality: DisagreementProfile) -> bool:
        """Check if we should force a disagreement based on base disagreement rate."""
        return random.random() < personality.base_disagreement_rate

    def _force_disagreement(self, decision: AccountDecision, signal: OriginalSignal) -> AccountDecision:
        """Force a disagreement by modifying or skipping the decision."""
        disagreement_type = random.choice(['skip', 'modify_significant'])
        
        if disagreement_type == 'skip':
            decision.decision = DecisionType.SKIP
            decision.reasoning = random.choice(SKIP_REASONS)
            
        else:  # modify_significant
            decision.decision = DecisionType.MODIFY
            
            # Make a significant modification
            modification_type = random.choice(['tp', 'sl', 'size', 'direction'])
            
            if modification_type == 'tp':
                decision.modifications.take_profit = signal.take_profit * random.uniform(0.6, 1.4)
                decision.reasoning = "Adjusted profit target based on personal analysis"
                
            elif modification_type == 'sl':
                decision.modifications.stop_loss = signal.stop_loss * random.uniform(0.7, 1.3)
                decision.reasoning = "Modified stop loss for better risk management"
                
            elif modification_type == 'size':
                decision.modifications.size = (decision.modifications.size or 0.01) * random.uniform(0.5, 0.8)
                decision.reasoning = "Reduced position size due to market uncertainty"
                
            elif modification_type == 'direction':
                decision.modifications.direction = 'short' if signal.direction.value == 'long' else 'long'
                decision.reasoning = "Personal analysis suggests opposite direction"
        
        return decision

    def _get_default_personality(self, personality_id: str) -> DisagreementProfile:
        """Create default personality for missing profiles."""
        from .models import DecisionBiases, SituationalModifiers, CorrelationAwareness
        
        return DisagreementProfile(
            personality_id=personality_id,
            base_disagreement_rate=0.175,
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