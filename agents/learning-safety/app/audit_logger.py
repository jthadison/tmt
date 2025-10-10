"""
Audit trail logging for autonomous learning cycles.

Provides structured logging for all learning cycle events with JSON format,
file rotation, and comprehensive event tracking for post-mortem analysis.
"""

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .models.performance_models import PerformanceAnalysis


class AuditLogger:
    """
    Audit trail logger for learning cycle events.

    Provides structured logging (JSON format) for learning cycle start,
    completion, and failure events with automatic file rotation.
    """

    def __init__(self, log_file_path: str = "agents/learning-safety/logs/audit_trail.log"):
        """
        Initialize audit logger with file rotation.

        Args:
            log_file_path: Path to audit log file (relative to project root)
        """
        self.logger = logging.getLogger("audit_trail")
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers if logger already configured
        if not self.logger.handlers:
            # Create logs directory if it doesn't exist
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Configure rotating file handler (max 100MB per file, keep last 10)
            handler = RotatingFileHandler(
                log_file_path,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10,
                encoding="utf-8"
            )
            handler.setLevel(logging.INFO)

            # Use JSON-like format for structured logging
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

            # Also add console handler for visibility
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_cycle_start(self, timestamp: datetime, cycle_id: str) -> None:
        """
        Log learning cycle start event.

        Args:
            timestamp: Cycle start timestamp
            cycle_id: Unique cycle identifier (UUID)
        """
        log_entry = {
            "event": "learning_cycle_start",
            "cycle_id": cycle_id,
            "timestamp": timestamp.isoformat(),
            "level": "INFO"
        }
        self.logger.info(json.dumps(log_entry))

    def log_cycle_complete(
        self,
        cycle_id: str,
        results: PerformanceAnalysis
    ) -> None:
        """
        Log learning cycle completion event.

        Args:
            cycle_id: Unique cycle identifier
            results: Performance analysis results from the cycle
        """
        log_entry = {
            "event": "learning_cycle_complete",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "trade_count": results.trade_count,
            "best_session": results.best_session,
            "worst_session": results.worst_session,
            "suggestions_count": 0,  # Will be populated by suggestion engine in future stories
            "session_metrics": {
                session: {
                    "total_trades": metrics.total_trades,
                    "win_rate": float(metrics.win_rate),
                    "avg_rr": float(metrics.avg_rr),
                    "profit_factor": float(metrics.profit_factor),
                    "total_pnl": float(metrics.total_pnl)
                }
                for session, metrics in results.session_metrics.items()
            }
        }
        self.logger.info(json.dumps(log_entry))

    def log_cycle_failed(self, cycle_id: str, error: Exception) -> None:
        """
        Log learning cycle failure event.

        Args:
            cycle_id: Unique cycle identifier
            error: Exception that caused the failure
        """
        log_entry = {
            "event": "learning_cycle_failed",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "error_message": str(error),
            "error_type": type(error).__name__
        }
        self.logger.error(json.dumps(log_entry))

    def log_database_unavailable(self, cycle_id: str, error: Exception) -> None:
        """
        Log database unavailability event (non-fatal, cycle skipped).

        Args:
            cycle_id: Unique cycle identifier
            error: Exception from database connection attempt
        """
        log_entry = {
            "event": "database_unavailable",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "error_message": str(error),
            "action": "cycle_skipped"
        }
        self.logger.warning(json.dumps(log_entry))

    def log_insufficient_data(
        self,
        cycle_id: str,
        trade_count: int,
        min_required: int
    ) -> None:
        """
        Log insufficient data event.

        Args:
            cycle_id: Unique cycle identifier
            trade_count: Number of trades available
            min_required: Minimum trades required for analysis
        """
        log_entry = {
            "event": "insufficient_data",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "trade_count": trade_count,
            "min_required": min_required,
            "action": "analysis_skipped"
        }
        self.logger.info(json.dumps(log_entry))
