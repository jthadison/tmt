"""
Audit trail logger with file storage and querying capabilities.

This module provides comprehensive audit logging for all emergency actions
in the trading system, including emergency stops, position closures,
rollbacks, and circuit breaker resets.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from logging.handlers import RotatingFileHandler


class AuditLogger:
    """Audit trail logger with file storage and querying"""

    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        self.logger = logging.getLogger("audit_trail")
        self.logger.handlers.clear()  # Clear any existing handlers

        handler = RotatingFileHandler(
            self.log_dir / "audit.log",
            maxBytes=10 * 1024 * 1024,  # 10MB per file
            backupCount=10
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Prevent duplicate logs

    def log(self, entry: Dict[str, Any]):
        """Log an audit entry"""
        # Add metadata
        entry["log_id"] = f"{datetime.now().timestamp()}_{entry.get('user', 'unknown')}"
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()

        # Write to log file as JSON
        self.logger.info(json.dumps(entry))

    def query_logs(
        self,
        action_type: Optional[str] = None,
        user: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters"""
        logs = []

        # Read log files (current + rotated backups)
        log_files = sorted(self.log_dir.glob("audit.log*"), reverse=True)

        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())

                            # Apply filters
                            if action_type and entry.get("action_type") != action_type:
                                continue
                            if user and entry.get("user") != user:
                                continue
                            if start_date:
                                entry_time = datetime.fromisoformat(entry["timestamp"])
                                if entry_time < start_date:
                                    continue
                            if end_date:
                                entry_time = datetime.fromisoformat(entry["timestamp"])
                                if entry_time > end_date:
                                    continue
                            if status is not None and entry.get("success") != status:
                                continue

                            logs.append(entry)

                            if len(logs) >= limit:
                                return logs
                        except json.JSONDecodeError:
                            continue
            except FileNotFoundError:
                continue

        return logs


# Global instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
