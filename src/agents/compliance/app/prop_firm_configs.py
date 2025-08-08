"""
Prop Firm Rule Configurations

Defines rule sets for DNA Funded, Funding Pips, and The Funded Trader
based on PROP_FIRM_SPECIFICATIONS.md
"""

from typing import Dict, Any, List
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel


class PropFirm(str, Enum):
    DNA_FUNDED = "dna_funded"
    FUNDING_PIPS = "funding_pips"
    THE_FUNDED_TRADER = "the_funded_trader"


class AccountPhase(str, Enum):
    CHALLENGE_PHASE_1 = "challenge_phase_1"
    CHALLENGE_PHASE_2 = "challenge_phase_2"
    EVALUATION = "evaluation"
    FUNDED = "funded"
    RAPID = "rapid"
    KNIGHT = "knight"


class TradingPlatform(str, Enum):
    TRADELOCKER = "tradelocker"
    DXTRADE = "dxtrade"


class PropFirmRuleConfig(BaseModel):
    """Base configuration for prop firm rules"""
    firm_name: PropFirm
    daily_loss_limit_pct: Decimal
    max_drawdown_pct: Decimal
    trailing_drawdown: bool
    min_trading_days: int
    news_buffer_minutes: int
    max_concurrent_positions: int
    min_hold_time_seconds: int
    weekend_closure_required: bool
    mandatory_stop_loss: bool
    primary_platform: TradingPlatform
    secondary_platform: TradingPlatform
    
    # Position sizing rules
    max_lot_sizes: Dict[str, Decimal]  # Account size -> max lots
    max_risk_per_trade_pct: Decimal
    
    # Leverage limits
    forex_leverage: int
    indices_leverage: int
    
    # Profit targets by phase
    profit_targets: Dict[AccountPhase, Decimal]
    
    # Special rules
    consistency_rules: Dict[str, Any]
    prohibited_strategies: List[str]
    
    # Payout structure
    profit_split_pct: Decimal  # Trader's percentage
    first_payout_days: int


# DNA Funded Configuration
DNA_FUNDED_CONFIG = PropFirmRuleConfig(
    firm_name=PropFirm.DNA_FUNDED,
    daily_loss_limit_pct=Decimal("0.05"),  # 5%
    max_drawdown_pct=Decimal("0.10"),      # 10%
    trailing_drawdown=True,
    min_trading_days=5,
    news_buffer_minutes=2,
    max_concurrent_positions=5,
    min_hold_time_seconds=0,  # No minimum
    weekend_closure_required=False,
    mandatory_stop_loss=False,
    primary_platform=TradingPlatform.TRADELOCKER,
    secondary_platform=TradingPlatform.DXTRADE,
    
    max_lot_sizes={
        "10000": Decimal("2.0"),    # $10k -> 2 lots
        "25000": Decimal("5.0"),    # $25k -> 5 lots
        "50000": Decimal("10.0"),   # $50k -> 10 lots
        "100000": Decimal("20.0"),  # $100k -> 20 lots
    },
    max_risk_per_trade_pct=Decimal("0.05"),  # 5%
    
    forex_leverage=100,
    indices_leverage=100,
    
    profit_targets={
        AccountPhase.CHALLENGE_PHASE_1: Decimal("0.08"),  # 8%
        AccountPhase.CHALLENGE_PHASE_2: Decimal("0.05"),  # 5%
        AccountPhase.FUNDED: Decimal("0.0"),              # No target
    },
    
    consistency_rules={
        "daily_profit_cap_pct": Decimal("0.30"),  # 30% of total profit max
        "lot_size_variance_max": 3.0,             # 3x max variance
    },
    
    prohibited_strategies=[
        "grid_trading",
        "martingale",
        "high_frequency_trading",  # >100 trades/day
        "arbitrage"
    ],
    
    profit_split_pct=Decimal("0.80"),  # 80% to trader
    first_payout_days=30
)


# Funding Pips Configuration
FUNDING_PIPS_CONFIG = PropFirmRuleConfig(
    firm_name=PropFirm.FUNDING_PIPS,
    daily_loss_limit_pct=Decimal("0.04"),  # 4%
    max_drawdown_pct=Decimal("0.08"),       # 8%
    trailing_drawdown=False,  # Static drawdown
    min_trading_days=3,
    news_buffer_minutes=0,  # News trading allowed
    max_concurrent_positions=999,  # No limit within risk
    min_hold_time_seconds=60,  # 1 minute minimum
    weekend_closure_required=True,
    mandatory_stop_loss=True,
    primary_platform=TradingPlatform.DXTRADE,
    secondary_platform=TradingPlatform.TRADELOCKER,
    
    max_lot_sizes={},  # Risk-based calculation only
    max_risk_per_trade_pct=Decimal("0.02"),  # 2%
    
    forex_leverage=30,
    indices_leverage=20,
    
    profit_targets={
        AccountPhase.EVALUATION: Decimal("0.08"),  # 8%
        AccountPhase.FUNDED: Decimal("0.0"),       # No target
    },
    
    consistency_rules={},  # No specific consistency rules
    
    prohibited_strategies=[
        "copy_trading",
        "tick_scalping",
        "latency_arbitrage"
    ],
    
    profit_split_pct=Decimal("0.85"),  # 85% to trader
    first_payout_days=14
)


# The Funded Trader Configuration
THE_FUNDED_TRADER_CONFIG = PropFirmRuleConfig(
    firm_name=PropFirm.THE_FUNDED_TRADER,
    daily_loss_limit_pct=Decimal("0.05"),  # 5%
    max_drawdown_pct=Decimal("0.10"),       # 10%
    trailing_drawdown=True,
    min_trading_days=5,
    news_buffer_minutes=5,  # Standard/Rapid: 5 min buffer
    max_concurrent_positions=10,
    min_hold_time_seconds=0,  # No minimum
    weekend_closure_required=False,
    mandatory_stop_loss=False,
    primary_platform=TradingPlatform.TRADELOCKER,
    secondary_platform=TradingPlatform.DXTRADE,
    
    max_lot_sizes={
        "10000": Decimal("5.0"),    # Tier 1: 5 lots
        "25000": Decimal("5.0"),    # Tier 1: 5 lots
        "50000": Decimal("10.0"),   # Tier 2: 10 lots
        "100000": Decimal("20.0"),  # Tier 3: 20 lots
        "200000": Decimal("40.0"),  # Tier 4: 40 lots
    },
    max_risk_per_trade_pct=Decimal("0.05"),  # 5%
    
    forex_leverage=100,  # Can be 200 for experienced
    indices_leverage=100,
    
    profit_targets={
        AccountPhase.CHALLENGE_PHASE_1: Decimal("0.10"),  # Standard Phase 1: 10%
        AccountPhase.CHALLENGE_PHASE_2: Decimal("0.05"),  # Standard Phase 2: 5%
        AccountPhase.RAPID: Decimal("0.08"),              # Rapid: 8%
        AccountPhase.KNIGHT: Decimal("0.15"),             # Knight: 15%
        AccountPhase.FUNDED: Decimal("0.0"),              # No target
    },
    
    consistency_rules={
        "scaling_enabled": True,
        "scale_increase_pct": Decimal("0.25"),      # 25% increase
        "scale_frequency_months": 3,
        "scale_profit_requirement_pct": Decimal("0.10"),  # 10% profit needed
        "max_account_size": Decimal("1000000"),     # $1M max
    },
    
    prohibited_strategies=[
        "account_management_third_party",
        "reverse_arbitrage",
        "demo_server_delay_exploitation"
    ],
    
    profit_split_pct=Decimal("0.80"),  # 80% initially, 90% after scaling
    first_payout_days=30
)


# Configuration registry
PROP_FIRM_CONFIGS: Dict[PropFirm, PropFirmRuleConfig] = {
    PropFirm.DNA_FUNDED: DNA_FUNDED_CONFIG,
    PropFirm.FUNDING_PIPS: FUNDING_PIPS_CONFIG,
    PropFirm.THE_FUNDED_TRADER: THE_FUNDED_TRADER_CONFIG,
}


def get_prop_firm_config(firm: PropFirm) -> PropFirmRuleConfig:
    """Get configuration for specified prop firm"""
    return PROP_FIRM_CONFIGS[firm]


def get_all_prop_firms() -> List[PropFirm]:
    """Get list of all supported prop firms"""
    return list(PROP_FIRM_CONFIGS.keys())