"""
Funding Pips specific compliance implementation.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from .models import (
    Account, ComplianceStatus, Trade, ValidationResult, 
    ViolationType, Position
)
from .rules_engine import RulesEngine

logger = logging.getLogger(__name__)


class FundingPipsWarningLevel(Enum):
    """Warning levels for Funding Pips daily loss."""
    LEVEL_80 = "80_percent"
    LEVEL_90 = "90_percent"
    LEVEL_95 = "95_percent"
    CRITICAL = "critical"


class FundingPipsConfig(BaseModel):
    """Funding Pips configuration model."""
    version: str
    last_updated: str
    prop_firm: str
    enabled: bool
    feature_flags: Dict[str, bool]
    risk_management: Dict[str, any]
    position_management: Dict[str, any]
    trading_restrictions: Dict[str, any]
    account_management: Dict[str, any]
    monitoring: Dict[str, any]
    enforcement_priority: List[str]


class FundingPipsCompliance:
    """Funding Pips specific compliance engine."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Funding Pips compliance engine."""
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "funding_pips_config.json"
        self.config = self._load_config()
        self.rules_engine = RulesEngine()
        self.weekend_closure_scheduled = False
        
    def _load_config(self) -> FundingPipsConfig:
        """Load Funding Pips configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            return FundingPipsConfig(**config_data)
        except Exception as e:
            logger.error(f"Failed to load Funding Pips config: {e}")
            raise
    
    def validate_trade(self, account: Account, trade: Trade) -> ValidationResult:
        """
        Validate trade against Funding Pips rules.
        
        Returns:
            ValidationResult with approval status and any violations
        """
        violations = []
        
        # Check feature flags
        if not self.config.enabled:
            return ValidationResult(approved=True, violations=[])
        
        # Priority order enforcement
        for rule in self.config.enforcement_priority:
            if rule == "max_drawdown":
                if self._check_static_drawdown(account):
                    violations.append({
                        "type": ViolationType.MAX_DRAWDOWN.value,
                        "message": f"Static drawdown limit {self.config.risk_management['max_drawdown']*100}% exceeded",
                        "severity": "critical"
                    })
                    
            elif rule == "daily_loss_limit":
                daily_loss_check = self._check_daily_loss(account, trade)
                if daily_loss_check[0]:
                    violations.append({
                        "type": ViolationType.DAILY_LOSS.value,
                        "message": daily_loss_check[1],
                        "severity": daily_loss_check[2]
                    })
                    
            elif rule == "mandatory_stop_loss":
                if not trade.stop_loss:
                    violations.append({
                        "type": "MISSING_STOP_LOSS",
                        "message": "Funding Pips requires mandatory stop loss on all trades",
                        "severity": "critical"
                    })
                elif not self._validate_stop_loss_risk(account, trade):
                    violations.append({
                        "type": "EXCESSIVE_RISK",
                        "message": f"Stop loss exceeds {self.config.risk_management['max_risk_per_trade']*100}% risk limit",
                        "severity": "critical"
                    })
        
        # Check prohibited strategies
        if self._is_prohibited_strategy(trade):
            violations.append({
                "type": "PROHIBITED_STRATEGY",
                "message": f"Strategy {trade.strategy} is prohibited by Funding Pips",
                "severity": "critical"
            })
        
        # Check leverage limits
        leverage_violation = self._check_leverage(trade)
        if leverage_violation:
            violations.append(leverage_violation)
        
        # Determine if trade should be approved
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        approved = len(critical_violations) == 0
        
        return ValidationResult(
            approved=approved,
            violations=violations,
            warnings=[v for v in violations if v["severity"] == "warning"]
        )
    
    def _check_static_drawdown(self, account: Account) -> bool:
        """Check if account has exceeded static drawdown limit."""
        initial_balance = account.initial_balance
        current_equity = account.balance + account.unrealized_pnl
        
        drawdown = (initial_balance - current_equity) / initial_balance
        max_drawdown = Decimal(str(self.config.risk_management["max_drawdown"]))
        
        return drawdown >= max_drawdown
    
    def _check_daily_loss(self, account: Account, trade: Trade) -> Tuple[bool, str, str]:
        """
        Check daily loss limit with warning levels.
        
        Returns:
            Tuple of (violation, message, severity)
        """
        daily_loss_limit = Decimal(str(self.config.risk_management["daily_loss_limit"]))
        daily_pnl_ratio = abs(account.daily_pnl / account.initial_balance)
        
        # Calculate potential loss from new trade
        potential_loss = self._calculate_potential_loss(trade)
        potential_daily_ratio = (abs(account.daily_pnl) + potential_loss) / account.initial_balance
        
        # Check warning levels
        warning_levels = self.config.risk_management["daily_loss_warning_levels"]
        
        if potential_daily_ratio >= daily_loss_limit:
            return (True, f"Trade would exceed 4% daily loss limit", "critical")
        elif potential_daily_ratio >= Decimal(str(warning_levels[2])):  # 95%
            return (True, f"Daily loss at 95% of limit ({potential_daily_ratio*100:.2f}%)", "warning")
        elif potential_daily_ratio >= Decimal(str(warning_levels[1])):  # 90%
            return (True, f"Daily loss at 90% of limit ({potential_daily_ratio*100:.2f}%)", "warning")
        elif potential_daily_ratio >= Decimal(str(warning_levels[0])):  # 80%
            return (True, f"Daily loss at 80% of limit ({potential_daily_ratio*100:.2f}%)", "info")
        
        return (False, "", "")
    
    def _validate_stop_loss_risk(self, account: Account, trade: Trade) -> bool:
        """Validate stop loss is within 2% risk limit."""
        if not trade.stop_loss:
            return False
            
        # Calculate risk as percentage of account
        risk_amount = abs(trade.entry_price - trade.stop_loss) * trade.position_size
        risk_percentage = risk_amount / account.balance
        max_risk = Decimal(str(self.config.risk_management["max_risk_per_trade"]))
        
        return risk_percentage <= max_risk
    
    def _calculate_potential_loss(self, trade: Trade) -> Decimal:
        """Calculate potential loss from trade."""
        if trade.stop_loss:
            return abs(trade.entry_price - trade.stop_loss) * trade.position_size
        else:
            # Use max risk per trade as fallback
            return trade.position_size * trade.entry_price * Decimal(str(self.config.risk_management["max_risk_per_trade"]))
    
    def _is_prohibited_strategy(self, trade: Trade) -> bool:
        """Check if trade uses prohibited strategy."""
        if not hasattr(trade, 'strategy') or not trade.strategy:
            return False
        
        prohibited = self.config.trading_restrictions["prohibited_strategies"]
        return trade.strategy.lower() in [s.lower() for s in prohibited]
    
    def _check_leverage(self, trade: Trade) -> Optional[Dict]:
        """Check if trade exceeds leverage limits."""
        max_leverage = self.config.trading_restrictions["max_leverage"]
        
        # Determine instrument type
        instrument_type = self._get_instrument_type(trade.symbol)
        if not instrument_type:
            return None
            
        if instrument_type not in max_leverage:
            return None
            
        # Calculate actual leverage
        actual_leverage = trade.position_size * trade.entry_price / trade.margin_required
        
        if actual_leverage > max_leverage[instrument_type]:
            return {
                "type": "EXCESSIVE_LEVERAGE",
                "message": f"Leverage {actual_leverage:.1f}x exceeds {instrument_type} limit of {max_leverage[instrument_type]}x",
                "severity": "critical"
            }
        
        return None
    
    def _get_instrument_type(self, symbol: str) -> Optional[str]:
        """Determine instrument type from symbol."""
        symbol_upper = symbol.upper()
        
        # Forex pairs
        forex_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD']
        if any(curr in symbol_upper for curr in forex_currencies):
            return "forex"
        
        # Indices
        indices = ['SPX', 'NDX', 'DJI', 'DAX', 'FTSE', 'NKY']
        if any(idx in symbol_upper for idx in indices):
            return "indices"
        
        # Commodities
        commodities = ['GOLD', 'XAU', 'SILVER', 'XAG', 'OIL', 'WTI', 'BRENT']
        if any(comm in symbol_upper for comm in commodities):
            return "commodities"
        
        # Crypto
        crypto = ['BTC', 'ETH', 'CRYPTO']
        if any(cry in symbol_upper for cry in crypto):
            return "crypto"
        
        return "forex"  # Default to forex
    
    def check_minimum_hold_time(self, position: Position) -> Tuple[bool, Optional[int]]:
        """
        Check if position meets minimum hold time requirement.
        
        Returns:
            Tuple of (meets_requirement, seconds_remaining)
        """
        if not self.config.feature_flags.get("enforce_min_hold_time", True):
            return (True, None)
        
        min_hold_seconds = self.config.position_management["min_hold_time_seconds"]
        
        # Calculate time held
        time_held = (datetime.utcnow() - position.open_time).total_seconds()
        
        if time_held >= min_hold_seconds:
            return (True, None)
        else:
            seconds_remaining = int(min_hold_seconds - time_held)
            return (False, seconds_remaining)
    
    def check_weekend_closure(self, positions: List[Position]) -> List[Position]:
        """
        Check which positions need weekend closure.
        
        Returns:
            List of positions that must be closed
        """
        if not self.config.feature_flags.get("enforce_weekend_closure", True):
            return []
        
        if not self.config.position_management["weekend_closure_required"]:
            return []
        
        # Parse closure time
        closure_time_str = self.config.position_management["weekend_closure_time"]
        closure_tz = ZoneInfo(self.config.position_management["weekend_closure_timezone"])
        
        now = datetime.now(closure_tz)
        
        # Check if it's Friday
        if now.weekday() != 4:  # 4 = Friday
            return []
        
        # Parse closure time
        closure_hour, closure_minute = map(int, closure_time_str.split(':'))
        closure_time = now.replace(hour=closure_hour, minute=closure_minute, second=0)
        
        # Add grace period
        grace_minutes = self.config.position_management.get("weekend_closure_grace_period_minutes", 5)
        final_closure = closure_time + timedelta(minutes=grace_minutes)
        
        # Check if we're in the closure window
        if closure_time <= now <= final_closure:
            return positions  # All positions must be closed
        
        return []
    
    def calculate_auto_stop_loss(self, account: Account, entry_price: Decimal, 
                                position_size: Decimal, direction: str) -> Decimal:
        """
        Calculate automatic stop loss based on 2% risk rule.
        
        Args:
            account: Trading account
            entry_price: Trade entry price
            position_size: Position size in lots
            direction: 'buy' or 'sell'
            
        Returns:
            Calculated stop loss price
        """
        max_risk = Decimal(str(self.config.risk_management["max_risk_per_trade"]))
        risk_amount = account.balance * max_risk
        
        # Calculate price movement for 2% risk
        price_movement = risk_amount / position_size
        
        if direction.lower() == 'buy':
            stop_loss = entry_price - price_movement
        else:
            stop_loss = entry_price + price_movement
        
        return stop_loss
    
    def get_compliance_dashboard_data(self, account: Account) -> Dict:
        """
        Get compliance data for dashboard display.
        
        Returns:
            Dictionary with compliance metrics and status
        """
        initial_balance = account.initial_balance
        current_equity = account.balance + account.unrealized_pnl
        
        # Calculate metrics
        daily_loss_pct = abs(account.daily_pnl / initial_balance) * 100
        static_drawdown_pct = ((initial_balance - current_equity) / initial_balance) * 100
        
        # Warning levels
        warning_levels = [w * 100 for w in self.config.risk_management["daily_loss_warning_levels"]]
        daily_loss_limit = self.config.risk_management["daily_loss_limit"] * 100
        max_drawdown_limit = self.config.risk_management["max_drawdown"] * 100
        
        # Determine status colors
        daily_loss_status = "green"
        if daily_loss_pct >= warning_levels[2]:  # 95%
            daily_loss_status = "red"
        elif daily_loss_pct >= warning_levels[1]:  # 90%
            daily_loss_status = "orange"
        elif daily_loss_pct >= warning_levels[0]:  # 80%
            daily_loss_status = "yellow"
        
        drawdown_status = "green"
        if static_drawdown_pct >= max_drawdown_limit * 0.95:
            drawdown_status = "red"
        elif static_drawdown_pct >= max_drawdown_limit * 0.8:
            drawdown_status = "yellow"
        
        return {
            "prop_firm": "Funding Pips",
            "daily_loss": {
                "current": f"{daily_loss_pct:.2f}%",
                "limit": f"{daily_loss_limit:.1f}%",
                "status": daily_loss_status,
                "remaining": f"{daily_loss_limit - daily_loss_pct:.2f}%"
            },
            "drawdown": {
                "current": f"{static_drawdown_pct:.2f}%",
                "limit": f"{max_drawdown_limit:.1f}%",
                "type": "static",
                "status": drawdown_status,
                "remaining": f"{max_drawdown_limit - static_drawdown_pct:.2f}%"
            },
            "rules": {
                "stop_loss_required": self.config.position_management["mandatory_stop_loss"],
                "min_hold_time": f"{self.config.position_management['min_hold_time_seconds']}s",
                "weekend_closure": self.config.position_management["weekend_closure_required"],
                "max_leverage": self.config.trading_restrictions["max_leverage"]
            },
            "compliance_score": self._calculate_compliance_score(account),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _calculate_compliance_score(self, account: Account) -> int:
        """
        Calculate compliance score (0-100).
        
        Based on:
        - Distance from limits
        - Recent violations
        - Trading consistency
        """
        score = 100
        
        # Deduct for proximity to limits
        daily_loss_ratio = abs(account.daily_pnl / account.initial_balance)
        if daily_loss_ratio > 0.032:  # 80% of limit
            score -= int((daily_loss_ratio - 0.032) * 500)
        
        current_equity = account.balance + account.unrealized_pnl
        drawdown = (account.initial_balance - current_equity) / account.initial_balance
        if drawdown > 0.064:  # 80% of limit
            score -= int((drawdown - 0.064) * 312.5)
        
        # Ensure score stays in valid range
        return max(0, min(100, score))