"""
Risk Assessment Engine - Evaluates risk levels for trading decisions.
Used to determine if accounts should skip signals due to risk preferences.
"""
import logging
from typing import Dict
from datetime import datetime

from .models import (
    RiskAssessment, OriginalSignal, DisagreementProfile
)

logger = logging.getLogger(__name__)


class RiskAssessmentEngine:
    """
    Evaluates risk levels for account trading decisions.
    
    Combines personal risk preferences, market conditions, and portfolio state
    to determine if a signal should be skipped for risk management reasons.
    """
    
    def __init__(self):
        # Market risk factors (would be populated from real market data)
        self.market_volatility = 0.3  # Current market volatility (0-1)
        self.news_risk_level = 0.2    # Current news-based risk (0-1)
        self.session_risk = 0.1       # Session-specific risk (0-1)
        
        logger.info("RiskAssessmentEngine initialized")

    def assess_risk(
        self,
        signal: OriginalSignal,
        account: Dict,
        personality: DisagreementProfile
    ) -> RiskAssessment:
        """
        Assess overall risk level for an account decision.
        
        Args:
            signal: The trading signal being evaluated
            account: Account configuration and current state
            personality: Risk preferences and biases
            
        Returns:
            Complete risk assessment with threshold comparison
        """
        logger.debug(f"Assessing risk for account {account['id']} on {signal.symbol}")
        
        # Calculate individual risk components
        personal_risk = self._calculate_personal_risk_level(signal, account, personality)
        market_risk = self._calculate_market_risk_level(signal)
        portfolio_risk = self._calculate_portfolio_risk_level(signal, account)
        
        # Combine risk levels with weights
        combined_risk = self._combine_risk_levels(personal_risk, market_risk, portfolio_risk)
        
        # Determine personal risk threshold based on personality
        risk_threshold = self._determine_risk_threshold(personality)
        
        assessment = RiskAssessment(
            personal_risk_level=personal_risk,
            market_risk_level=market_risk,
            portfolio_risk_level=portfolio_risk,
            combined_risk_level=combined_risk,
            risk_threshold=risk_threshold
        )
        
        logger.debug(f"Risk assessment: Personal={personal_risk:.2f}, Market={market_risk:.2f}, "
                    f"Portfolio={portfolio_risk:.2f}, Combined={combined_risk:.2f}, "
                    f"Threshold={risk_threshold:.2f}")
        
        return assessment

    def _calculate_personal_risk_level(
        self,
        signal: OriginalSignal,
        account: Dict,
        personality: DisagreementProfile
    ) -> float:
        """Calculate risk level based on personal preferences and biases."""
        
        # Base personal risk from signal strength and personal skepticism
        signal_confidence = signal.strength
        skepticism = personality.biases.signal_skepticism
        
        # Lower confidence signals are riskier for skeptical personalities
        confidence_risk = (1.0 - signal_confidence) * (1.0 + skepticism)
        
        # Risk aversion affects perception of risk
        risk_aversion = personality.biases.risk_aversion
        risk_multiplier = 1.0 + risk_aversion * 0.5
        
        personal_risk = min(1.0, confidence_risk * risk_multiplier)
        
        logger.debug(f"Personal risk: confidence_risk={confidence_risk:.2f}, "
                    f"risk_aversion={risk_aversion:.2f}, final={personal_risk:.2f}")
        
        return personal_risk

    def _calculate_market_risk_level(self, signal: OriginalSignal) -> float:
        """Calculate risk level based on current market conditions."""
        
        # Combine various market risk factors
        volatility_risk = self.market_volatility
        news_risk = self.news_risk_level  
        session_risk = self.session_risk
        
        # Currency pair specific risk (placeholder - could be expanded)
        pair_risk = self._get_pair_risk(signal.symbol)
        
        # Combine market risk factors
        market_risk = min(1.0, (volatility_risk + news_risk + session_risk + pair_risk) / 4.0)
        
        logger.debug(f"Market risk: volatility={volatility_risk:.2f}, news={news_risk:.2f}, "
                    f"session={session_risk:.2f}, pair={pair_risk:.2f}, final={market_risk:.2f}")
        
        return market_risk

    def _calculate_portfolio_risk_level(self, signal: OriginalSignal, account: Dict) -> float:
        """Calculate risk level based on current portfolio state."""
        
        # Current drawdown risk
        current_drawdown = account.get('current_drawdown_pct', 0.0)
        drawdown_risk = min(1.0, current_drawdown / 10.0)  # Risk increases with drawdown
        
        # Exposure concentration risk  
        current_positions = account.get('open_positions', [])
        symbol_exposure = sum(1 for pos in current_positions if pos.get('symbol') == signal.symbol)
        concentration_risk = min(0.8, symbol_exposure * 0.2)  # Risk per additional position
        
        # Daily/weekly trade count risk
        daily_trades = account.get('daily_trade_count', 0)
        overtrading_risk = min(0.5, max(0.0, (daily_trades - 5) * 0.1))  # Risk after 5 trades
        
        # Account size relative to position size
        account_balance = account.get('balance', 10000)
        position_size = account.get('base_position_size', 0.01) * account_balance
        size_risk = min(0.3, position_size / account_balance * 10)  # Risk based on position size
        
        portfolio_risk = min(1.0, drawdown_risk + concentration_risk + overtrading_risk + size_risk)
        
        logger.debug(f"Portfolio risk: drawdown={drawdown_risk:.2f}, concentration={concentration_risk:.2f}, "
                    f"overtrading={overtrading_risk:.2f}, size={size_risk:.2f}, final={portfolio_risk:.2f}")
        
        return portfolio_risk

    def _combine_risk_levels(
        self, 
        personal_risk: float, 
        market_risk: float, 
        portfolio_risk: float
    ) -> float:
        """Combine individual risk levels into overall assessment."""
        
        # Weighted combination of risk factors
        personal_weight = 0.4
        market_weight = 0.3  
        portfolio_weight = 0.3
        
        combined = (
            personal_risk * personal_weight +
            market_risk * market_weight +
            portfolio_risk * portfolio_weight
        )
        
        # Apply non-linear scaling to emphasize high risk scenarios
        if combined > 0.7:
            combined = 0.7 + (combined - 0.7) * 1.5  # Amplify high risk
        
        return min(1.0, combined)

    def _determine_risk_threshold(self, personality: DisagreementProfile) -> float:
        """Determine personal risk threshold based on personality."""
        
        # Base threshold from risk aversion
        risk_aversion = personality.biases.risk_aversion
        base_threshold = 0.3 + (risk_aversion * 0.5)  # Range: 0.3 to 0.8
        
        # Adjust for loss avoidance
        loss_avoidance = personality.biases.loss_avoidance
        loss_adjustment = loss_avoidance * 0.2  # Up to 0.2 adjustment
        
        # Adjust for signal skepticism
        skepticism = personality.biases.signal_skepticism
        skepticism_adjustment = skepticism * 0.15  # Up to 0.15 adjustment
        
        threshold = min(0.9, base_threshold + loss_adjustment + skepticism_adjustment)
        
        logger.debug(f"Risk threshold: base={base_threshold:.2f}, "
                    f"loss_adj={loss_adjustment:.2f}, skepticism_adj={skepticism_adjustment:.2f}, "
                    f"final={threshold:.2f}")
        
        return threshold

    def _get_pair_risk(self, symbol: str) -> float:
        """Get currency pair specific risk factors."""
        
        # Risk levels for different currency pairs (placeholder)
        pair_risks = {
            'EURUSD': 0.1,   # Major - low risk
            'GBPUSD': 0.15,  # Major but more volatile
            'USDJPY': 0.12,  # Major
            'AUDUSD': 0.2,   # Minor - higher risk
            'USDCAD': 0.18,  # Minor
            'NZDUSD': 0.25,  # Minor - higher risk
            'EURGBP': 0.22,  # Cross - moderate risk
            'EURJPY': 0.3,   # Cross - higher risk
            'GBPJPY': 0.35,  # Cross - high risk
            'XAUUSD': 0.4,   # Gold - high volatility
            'XAGUSD': 0.45,  # Silver - very high volatility
        }
        
        return pair_risks.get(symbol, 0.3)  # Default moderate risk

    def update_market_conditions(
        self,
        volatility: float,
        news_risk: float,
        session_risk: float
    ) -> None:
        """Update current market risk factors."""
        
        self.market_volatility = max(0.0, min(1.0, volatility))
        self.news_risk_level = max(0.0, min(1.0, news_risk))
        self.session_risk = max(0.0, min(1.0, session_risk))
        
        logger.info(f"Updated market conditions: volatility={self.market_volatility:.2f}, "
                   f"news_risk={self.news_risk_level:.2f}, session_risk={self.session_risk:.2f}")

    def get_risk_explanation(self, assessment: RiskAssessment) -> str:
        """Generate human-readable explanation of risk assessment."""
        
        explanations = []
        
        if assessment.personal_risk_level > 0.6:
            explanations.append("high personal risk tolerance exceeded")
        
        if assessment.market_risk_level > 0.5:
            explanations.append("elevated market conditions")
            
        if assessment.portfolio_risk_level > 0.5:
            explanations.append("portfolio risk constraints")
        
        if assessment.combined_risk_level > assessment.risk_threshold:
            explanations.append(f"combined risk {assessment.combined_risk_level:.2f} exceeds threshold {assessment.risk_threshold:.2f}")
        
        if not explanations:
            return "risk levels within acceptable parameters"
            
        return "Risk concerns: " + ", ".join(explanations)

    def should_skip_signal(self, assessment: RiskAssessment) -> bool:
        """Determine if signal should be skipped based on risk assessment."""
        return assessment.combined_risk_level > assessment.risk_threshold