"""
Position Sizing Alert Service

Alert generation for position sizing issues and thresholds.
"""

import logging
from decimal import Decimal
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PositionSizingAlertService:
    """
    Alert service for position sizing issues

    Features:
    - Low account balance alerts
    - Position size rejection alerts
    - Margin requirement alerts
    - Portfolio heat alerts
    """

    def __init__(
        self,
        min_balance_threshold: Decimal = Decimal("5000"),
        portfolio_heat_warning_threshold: Decimal = Decimal("0.12"),  # 12%
        portfolio_heat_critical_threshold: Decimal = Decimal("0.15"),  # 15%
    ):
        """
        Initialize alert service

        Args:
            min_balance_threshold: Minimum account balance threshold
            portfolio_heat_warning_threshold: Portfolio heat warning threshold
            portfolio_heat_critical_threshold: Portfolio heat critical threshold
        """
        self.min_balance_threshold = min_balance_threshold
        self.portfolio_heat_warning = portfolio_heat_warning_threshold
        self.portfolio_heat_critical = portfolio_heat_critical_threshold

        self.alerts_generated: List[dict] = []

        logger.info("PositionSizingAlertService initialized")

    async def check_account_balance(
        self,
        account_id: str,
        balance: Decimal
    ) -> Optional[dict]:
        """
        Check account balance and generate alert if below threshold

        Args:
            account_id: Account ID
            balance: Current balance

        Returns:
            Alert dictionary or None
        """
        if balance < self.min_balance_threshold:
            alert = {
                "level": AlertLevel.WARNING,
                "account_id": account_id,
                "type": "low_account_balance",
                "message": f"Account {account_id} balance ${balance:.2f} < ${self.min_balance_threshold:.2f}",
                "balance": float(balance),
                "threshold": float(self.min_balance_threshold),
                "recommendation": "Consider depositing funds or reducing position sizes"
            }

            logger.warning(alert["message"])
            self.alerts_generated.append(alert)

            return alert

        return None

    async def check_position_rejection(
        self,
        account_id: str,
        instrument: str,
        reason: str,
        details: Optional[dict] = None
    ) -> dict:
        """
        Alert when position size is rejected by broker

        Args:
            account_id: Account ID
            instrument: Instrument
            reason: Rejection reason
            details: Additional details

        Returns:
            Alert dictionary
        """
        alert = {
            "level": AlertLevel.CRITICAL,
            "account_id": account_id,
            "instrument": instrument,
            "type": "position_rejected",
            "message": f"Position rejected for {instrument}: {reason}",
            "reason": reason,
            "details": details or {},
            "recommendation": "Review position sizing parameters and account status"
        }

        logger.error(alert["message"])
        self.alerts_generated.append(alert)

        return alert

    async def check_margin_requirements(
        self,
        account_id: str,
        instrument: str,
        available_margin: Decimal,
        required_margin: Decimal,
        min_buffer: Decimal
    ) -> Optional[dict]:
        """
        Check margin requirements and generate alert if insufficient

        Args:
            account_id: Account ID
            instrument: Instrument
            available_margin: Available margin
            required_margin: Required margin
            min_buffer: Minimum margin buffer

        Returns:
            Alert dictionary or None
        """
        remaining_margin = available_margin - required_margin

        if remaining_margin < min_buffer:
            alert = {
                "level": AlertLevel.WARNING if remaining_margin > 0 else AlertLevel.CRITICAL,
                "account_id": account_id,
                "instrument": instrument,
                "type": "insufficient_margin",
                "message": f"Insufficient margin buffer for {instrument}: ${remaining_margin:.2f} < ${min_buffer:.2f}",
                "available_margin": float(available_margin),
                "required_margin": float(required_margin),
                "remaining_margin": float(remaining_margin),
                "min_buffer": float(min_buffer),
                "recommendation": "Close positions or deposit funds to increase margin"
            }

            logger.warning(alert["message"])
            self.alerts_generated.append(alert)

            return alert

        return None

    async def check_portfolio_heat(
        self,
        account_id: str,
        current_heat: Decimal
    ) -> Optional[dict]:
        """
        Check portfolio heat and generate alert if approaching limits

        Args:
            account_id: Account ID
            current_heat: Current portfolio heat (as decimal, e.g., 0.12 = 12%)

        Returns:
            Alert dictionary or None
        """
        if current_heat >= self.portfolio_heat_critical:
            alert = {
                "level": AlertLevel.CRITICAL,
                "account_id": account_id,
                "type": "portfolio_heat_critical",
                "message": f"Portfolio heat {current_heat:.1%} >= critical threshold {self.portfolio_heat_critical:.1%}",
                "current_heat": float(current_heat),
                "threshold": float(self.portfolio_heat_critical),
                "recommendation": "Reduce open positions immediately or halt new trades"
            }

            logger.critical(alert["message"])
            self.alerts_generated.append(alert)

            return alert

        elif current_heat >= self.portfolio_heat_warning:
            alert = {
                "level": AlertLevel.WARNING,
                "account_id": account_id,
                "type": "portfolio_heat_warning",
                "message": f"Portfolio heat {current_heat:.1%} approaching limit (threshold: {self.portfolio_heat_warning:.1%})",
                "current_heat": float(current_heat),
                "threshold": float(self.portfolio_heat_warning),
                "recommendation": "Consider reducing position sizes or limiting new trades"
            }

            logger.warning(alert["message"])
            self.alerts_generated.append(alert)

            return alert

        return None

    async def check_constraint_applied(
        self,
        account_id: str,
        instrument: str,
        constraint_type: str,
        original_size: int,
        limited_size: int
    ) -> dict:
        """
        Alert when position size constraint is applied

        Args:
            account_id: Account ID
            instrument: Instrument
            constraint_type: Type of constraint
            original_size: Original size
            limited_size: Limited size

        Returns:
            Alert dictionary
        """
        reduction_pct = ((original_size - limited_size) / original_size * 100) if original_size > 0 else 0

        alert = {
            "level": AlertLevel.INFO,
            "account_id": account_id,
            "instrument": instrument,
            "type": "constraint_applied",
            "constraint_type": constraint_type,
            "message": f"Position size reduced for {instrument}: {constraint_type} ({reduction_pct:.1f}% reduction)",
            "original_size": original_size,
            "limited_size": limited_size,
            "reduction_pct": reduction_pct,
            "recommendation": "Position size automatically adjusted to comply with risk limits"
        }

        logger.info(alert["message"])
        self.alerts_generated.append(alert)

        return alert

    def get_recent_alerts(
        self,
        limit: int = 10,
        level: Optional[AlertLevel] = None
    ) -> List[dict]:
        """
        Get recent alerts

        Args:
            limit: Maximum number of alerts to return
            level: Filter by alert level

        Returns:
            List of alert dictionaries
        """
        alerts = self.alerts_generated

        if level:
            alerts = [a for a in alerts if a["level"] == level]

        return alerts[-limit:]

    def clear_alerts(self):
        """Clear all stored alerts"""
        self.alerts_generated.clear()
        logger.info("All alerts cleared")
