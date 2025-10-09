"""
Position Sizing Integration for Orchestrator

Integrates EnhancedPositionSizer with orchestrator service while maintaining
backward compatibility with existing AdvancedPositionSizing interface.
"""

import sys
import os
import logging
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'shared', 'python-utils', 'src'))

from position_sizing import (
    EnhancedPositionSizer,
    PositionSizeResult,
    PositionSizingAuditLogger,
    PositionSizingAlertService
)

from .config import get_settings
from .models import TradeSignal

logger = logging.getLogger(__name__)


class IntegratedPositionSizing:
    """
    Integrated position sizing with enhanced calculations

    Provides a bridge between the orchestrator's existing interface
    and the new EnhancedPositionSizer implementation.
    """

    def __init__(self):
        """Initialize integrated position sizing"""
        self.settings = get_settings()

        # Initialize enhanced position sizer (will be set when OANDA client is available)
        self.enhanced_sizer: Optional[EnhancedPositionSizer] = None

        # Initialize audit logger
        self.audit_logger = PositionSizingAuditLogger(
            enable_file_logging=True,
            audit_file_path="logs/position_sizing_audit.log"
        )

        # Initialize alert service
        self.alert_service = PositionSizingAlertService(
            min_balance_threshold=Decimal("5000"),
            portfolio_heat_warning_threshold=Decimal("0.12"),
            portfolio_heat_critical_threshold=Decimal("0.15")
        )

        logger.info("IntegratedPositionSizing initialized")

    def initialize_with_oanda_client(self, oanda_client):
        """
        Initialize enhanced position sizer with OANDA client

        Args:
            oanda_client: OANDA API client instance
        """
        self.enhanced_sizer = EnhancedPositionSizer(
            oanda_client=oanda_client,
            account_currency="USD",
            balance_cache_ttl_minutes=5,
            min_account_balance=Decimal("5000"),
            max_per_trade_pct=Decimal("0.05"),  # 5%
            max_portfolio_heat_pct=Decimal("0.15"),  # 15%
            max_per_instrument_pct=Decimal("0.10"),  # 10%
            min_margin_buffer=Decimal("5000")
        )

        logger.info("EnhancedPositionSizer initialized with OANDA client")

    async def calculate_position_size(
        self,
        signal: TradeSignal,
        account_id: str,
        oanda_client,
        current_positions: Optional[List] = None
    ) -> PositionSizeResult:
        """
        Calculate position size using enhanced calculations

        Args:
            signal: Trading signal
            account_id: OANDA account ID
            oanda_client: OANDA client
            current_positions: Optional current positions (for backward compatibility)

        Returns:
            PositionSizeResult with detailed position sizing information
        """
        # Initialize enhanced sizer if not already done
        if self.enhanced_sizer is None:
            self.initialize_with_oanda_client(oanda_client)

        try:
            # Validate signal has required fields
            if not signal.entry_price or not signal.stop_loss:
                raise ValueError("Signal missing entry_price or stop_loss")

            # Determine direction
            direction = signal.direction.upper() if hasattr(signal, 'direction') else "BUY"

            # Calculate position size using enhanced sizer
            result = await self.enhanced_sizer.calculate_position_size(
                instrument=signal.instrument,
                entry_price=Decimal(str(signal.entry_price)),
                stop_loss=Decimal(str(signal.stop_loss)),
                account_id=account_id,
                direction=direction,
                risk_percent=Decimal("0.02"),  # 2% default risk
                take_profit=Decimal(str(signal.take_profit)) if signal.take_profit else None
            )

            # Log the decision for audit trail
            self.audit_logger.log_position_sizing_decision(
                account_id=account_id,
                instrument=signal.instrument,
                direction=direction,
                entry_price=Decimal(str(signal.entry_price)),
                stop_loss=Decimal(str(signal.stop_loss)),
                take_profit=Decimal(str(signal.take_profit)) if signal.take_profit else None,
                account_balance=result.account_balance,
                risk_percent=Decimal("0.02"),
                stop_distance_pips=result.stop_distance_pips,
                pip_value_account=result.pip_value_account,
                calculated_position_size=result.position_size,
                final_position_size=result.position_size,
                risk_amount=result.risk_amount,
                constraints_applied=result.constraints_applied,
                warnings=result.warnings,
                calculation_time_ms=result.calculation_time_ms,
                metadata=result.metadata
            )

            # Check for alerts
            await self._check_and_generate_alerts(
                account_id=account_id,
                result=result,
                signal=signal
            )

            # Log performance
            if result.calculation_time_ms > 50.0:
                logger.warning(
                    f"Position sizing exceeded 50ms target: "
                    f"{result.calculation_time_ms:.2f}ms"
                )

            return result

        except Exception as e:
            logger.error(f"Position size calculation failed: {e}", exc_info=True)
            raise

    async def _check_and_generate_alerts(
        self,
        account_id: str,
        result: PositionSizeResult,
        signal: TradeSignal
    ):
        """
        Check calculation results and generate alerts if needed

        Args:
            account_id: Account ID
            result: Position size result
            signal: Trade signal
        """
        # Check account balance
        await self.alert_service.check_account_balance(
            account_id=account_id,
            balance=result.account_balance
        )

        # Check constraints
        for constraint in result.constraints_applied:
            if constraint in ["per_trade_limit_5pct", "per_instrument_limit_10pct", "portfolio_heat_high"]:
                await self.alert_service.check_constraint_applied(
                    account_id=account_id,
                    instrument=signal.instrument,
                    constraint_type=constraint,
                    original_size=result.position_size,
                    limited_size=result.position_size
                )

    def get_statistics(self) -> Dict:
        """
        Get position sizing statistics

        Returns:
            Statistics dictionary
        """
        if self.enhanced_sizer:
            stats = self.enhanced_sizer.get_statistics()
            stats["recent_alerts"] = self.alert_service.get_recent_alerts(limit=10)
            return stats
        else:
            return {"error": "Enhanced sizer not initialized"}


# Global instance
_integrated_position_sizing: Optional[IntegratedPositionSizing] = None


def get_integrated_position_sizing() -> IntegratedPositionSizing:
    """Get global integrated position sizing instance"""
    global _integrated_position_sizing
    if _integrated_position_sizing is None:
        _integrated_position_sizing = IntegratedPositionSizing()
    return _integrated_position_sizing
