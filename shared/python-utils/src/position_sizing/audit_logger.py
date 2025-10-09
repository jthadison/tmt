"""
Position Sizing Audit Logger

Comprehensive audit trail for all position sizing decisions.
"""

import logging
import json
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PositionSizingAuditRecord:
    """
    Audit record for position sizing decision

    Attributes:
        timestamp: When the calculation occurred
        account_id: OANDA account ID
        instrument: Trading instrument
        direction: Trade direction (BUY/SELL)
        entry_price: Entry price level
        stop_loss: Stop loss price level
        take_profit: Optional take profit level
        account_balance: Account balance used
        risk_percent: Risk percentage applied
        stop_distance_pips: Stop loss distance in pips
        pip_value_account: Pip value in account currency
        calculated_position_size: Raw calculated position size
        final_position_size: Final position size after limits
        risk_amount: Risk amount in account currency
        constraints_applied: List of constraints applied
        warnings: List of warnings generated
        calculation_time_ms: Calculation time in milliseconds
        metadata: Additional metadata
    """
    timestamp: str
    account_id: str
    instrument: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    account_balance: float
    risk_percent: float
    stop_distance_pips: float
    pip_value_account: float
    calculated_position_size: int
    final_position_size: int
    risk_amount: float
    constraints_applied: list
    warnings: list
    calculation_time_ms: float
    metadata: dict


class PositionSizingAuditLogger:
    """
    Audit logger for position sizing decisions

    Features:
    - Structured logging of all position sizing calculations
    - JSON-serializable audit records
    - Support for external audit storage (database, files, etc.)
    - Performance metrics tracking
    """

    def __init__(
        self,
        enable_file_logging: bool = False,
        audit_file_path: Optional[str] = None
    ):
        """
        Initialize audit logger

        Args:
            enable_file_logging: Enable file-based audit logging
            audit_file_path: Path to audit log file (if file logging enabled)
        """
        self.enable_file_logging = enable_file_logging
        self.audit_file_path = audit_file_path

        if enable_file_logging and audit_file_path:
            # Set up file handler for audit logs
            file_handler = logging.FileHandler(audit_file_path)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger.info("PositionSizingAuditLogger initialized")

    def log_position_sizing_decision(
        self,
        account_id: str,
        instrument: str,
        direction: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Optional[Decimal],
        account_balance: Decimal,
        risk_percent: Decimal,
        stop_distance_pips: Decimal,
        pip_value_account: Decimal,
        calculated_position_size: int,
        final_position_size: int,
        risk_amount: Decimal,
        constraints_applied: list,
        warnings: list,
        calculation_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PositionSizingAuditRecord:
        """
        Log a position sizing decision

        Args:
            account_id: OANDA account ID
            instrument: Trading instrument
            direction: Trade direction (BUY/SELL)
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)
            account_balance: Account balance
            risk_percent: Risk percentage
            stop_distance_pips: Stop distance in pips
            pip_value_account: Pip value in account currency
            calculated_position_size: Raw calculated size
            final_position_size: Final size after limits
            risk_amount: Risk amount in account currency
            constraints_applied: Constraints applied
            warnings: Warnings generated
            calculation_time_ms: Calculation time
            metadata: Additional metadata

        Returns:
            PositionSizingAuditRecord
        """
        # Create audit record
        audit_record = PositionSizingAuditRecord(
            timestamp=datetime.utcnow().isoformat(),
            account_id=account_id,
            instrument=instrument,
            direction=direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit) if take_profit else None,
            account_balance=float(account_balance),
            risk_percent=float(risk_percent),
            stop_distance_pips=float(stop_distance_pips),
            pip_value_account=float(pip_value_account),
            calculated_position_size=calculated_position_size,
            final_position_size=final_position_size,
            risk_amount=float(risk_amount),
            constraints_applied=constraints_applied,
            warnings=warnings,
            calculation_time_ms=calculation_time_ms,
            metadata=metadata or {}
        )

        # Log as structured JSON
        audit_json = json.dumps(asdict(audit_record), indent=2)

        logger.info(
            f"Position sizing decision: {instrument} {direction} - "
            f"Size: {final_position_size} units, "
            f"Balance: ${account_balance:.2f}, "
            f"Risk: {risk_percent:.1%}, "
            f"Constraints: {', '.join(constraints_applied) if constraints_applied else 'None'}"
        )

        logger.debug(f"Full audit record:\n{audit_json}")

        return audit_record

    def log_validation_failure(
        self,
        account_id: str,
        instrument: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a position sizing validation failure

        Args:
            account_id: Account ID
            instrument: Instrument
            reason: Failure reason
            details: Additional details
        """
        failure_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "validation_failure",
            "account_id": account_id,
            "instrument": instrument,
            "reason": reason,
            "details": details or {}
        }

        logger.warning(
            f"Position sizing validation failed: {instrument} - "
            f"Reason: {reason}"
        )
        logger.debug(f"Failure details: {json.dumps(failure_record, indent=2)}")

    def log_constraint_applied(
        self,
        account_id: str,
        instrument: str,
        constraint_type: str,
        original_size: int,
        limited_size: int,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log when a constraint is applied to position size

        Args:
            account_id: Account ID
            instrument: Instrument
            constraint_type: Type of constraint
            original_size: Original calculated size
            limited_size: Size after constraint
            details: Additional details
        """
        constraint_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "constraint_applied",
            "account_id": account_id,
            "instrument": instrument,
            "constraint_type": constraint_type,
            "original_size": original_size,
            "limited_size": limited_size,
            "reduction_pct": ((original_size - limited_size) / original_size * 100) if original_size > 0 else 0,
            "details": details or {}
        }

        logger.info(
            f"Constraint applied: {constraint_type} - "
            f"{instrument} size reduced from {original_size} to {limited_size} units"
        )
        logger.debug(f"Constraint details: {json.dumps(constraint_record, indent=2)}")

    def log_performance_metrics(
        self,
        calculation_time_ms: float,
        cache_hit: bool,
        target_time_ms: float = 50.0
    ):
        """
        Log performance metrics for position sizing calculation

        Args:
            calculation_time_ms: Calculation time in milliseconds
            cache_hit: Whether cache was hit
            target_time_ms: Target calculation time (default: 50ms)
        """
        performance_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "performance_metrics",
            "calculation_time_ms": calculation_time_ms,
            "cache_hit": cache_hit,
            "target_time_ms": target_time_ms,
            "within_target": calculation_time_ms <= target_time_ms
        }

        if calculation_time_ms > target_time_ms:
            logger.warning(
                f"Position sizing calculation exceeded target: "
                f"{calculation_time_ms:.2f}ms > {target_time_ms:.2f}ms"
            )
        else:
            logger.debug(
                f"Position sizing performance: {calculation_time_ms:.2f}ms "
                f"(cache_hit: {cache_hit})"
            )
