"""
Comprehensive Audit Logging System

Provides detailed audit trails for all trading decisions and system activities.
Ensures compliance and enables forensic analysis of trading behavior.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class AuditEventType(Enum):
    """Types of audit events"""
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_PROCESSED = "signal_processed"
    TRADE_EXECUTED = "trade_executed"
    TRADE_CLOSED = "trade_closed"
    POSITION_MODIFIED = "position_modified"
    RISK_CHECK = "risk_check"
    DISAGREEMENT_DECISION = "disagreement_decision"
    PATTERN_DETECTED = "pattern_detected"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    EMERGENCY_STOP = "emergency_stop"
    VALIDATION_CHECK = "validation_check"
    RANDOM_USAGE_DETECTED = "random_usage_detected"


@dataclass
class AuditEvent:
    """Structured audit event"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    component: str
    description: str
    data: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    risk_level: str = "info"  # info, warning, critical
    compliance_relevant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['event_type'] = self.event_type.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


class AuditLogger:
    """Comprehensive audit logging system"""

    def __init__(self, log_directory: str = None):
        self.log_directory = Path(log_directory) if log_directory else Path("audit_logs")
        self.log_directory.mkdir(exist_ok=True)

        # Create daily log file
        self.current_date = datetime.now().date()
        self.current_log_file = self._get_log_file_path()

        # In-memory buffer for high-frequency events
        self.event_buffer: List[AuditEvent] = []
        self.buffer_max_size = 100
        self.buffer_flush_interval = 30  # seconds

        # Start background flush task
        self._flush_task = None
        self._start_flush_task()

        # Event counters
        self.event_counts: Dict[str, int] = {}

        logger = logging.getLogger(__name__)
        logger.info(f"Audit logger initialized: {self.current_log_file}")

    def _get_log_file_path(self) -> Path:
        """Get current log file path"""
        date_str = self.current_date.strftime("%Y%m%d")
        return self.log_directory / f"trading_audit_{date_str}.jsonl"

    def _start_flush_task(self):
        """Start background task to flush events"""
        try:
            loop = asyncio.get_event_loop()
            self._flush_task = loop.create_task(self._flush_loop())
        except RuntimeError:
            # No event loop running, manual flushing only
            pass

    async def _flush_loop(self):
        """Background task to periodically flush events"""
        while True:
            try:
                await asyncio.sleep(self.buffer_flush_interval)
                await self.flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in flush loop: {e}")

    def _generate_event_id(self, event_type: AuditEventType, component: str) -> str:
        """Generate unique event ID"""
        timestamp_str = datetime.now().isoformat()
        raw_id = f"{event_type.value}:{component}:{timestamp_str}"
        return hashlib.md5(raw_id.encode()).hexdigest()[:12]

    def log_event(self,
                  event_type: AuditEventType,
                  component: str,
                  description: str,
                  data: Dict[str, Any],
                  risk_level: str = "info",
                  compliance_relevant: bool = True) -> str:
        """Log an audit event"""

        event = AuditEvent(
            event_id=self._generate_event_id(event_type, component),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            component=component,
            description=description,
            data=data,
            risk_level=risk_level,
            compliance_relevant=compliance_relevant
        )

        # Add to buffer
        self.event_buffer.append(event)

        # Update counters
        event_key = f"{event_type.value}:{risk_level}"
        self.event_counts[event_key] = self.event_counts.get(event_key, 0) + 1

        # Flush if buffer is full
        if len(self.event_buffer) >= self.buffer_max_size:
            asyncio.create_task(self.flush_events())

        return event.event_id

    async def flush_events(self):
        """Flush buffered events to disk"""
        if not self.event_buffer:
            return

        # Check if date changed (new day = new log file)
        current_date = datetime.now().date()
        if current_date != self.current_date:
            self.current_date = current_date
            self.current_log_file = self._get_log_file_path()

        # Write events to file
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                for event in self.event_buffer:
                    json_line = json.dumps(event.to_dict(), ensure_ascii=False)
                    f.write(json_line + '\n')

            # Clear buffer
            events_written = len(self.event_buffer)
            self.event_buffer.clear()

            logger = logging.getLogger(__name__)
            logger.debug(f"Flushed {events_written} audit events to {self.current_log_file}")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to flush audit events: {e}")

    def log_signal_generated(self, signal_data: Dict[str, Any], agent_id: str):
        """Log signal generation event"""
        self.log_event(
            AuditEventType.SIGNAL_GENERATED,
            agent_id,
            f"Trading signal generated: {signal_data.get('signal_type', 'unknown')} {signal_data.get('symbol', 'unknown')}",
            {
                "signal_id": signal_data.get("signal_id"),
                "symbol": signal_data.get("symbol"),
                "signal_type": signal_data.get("signal_type"),
                "confidence": signal_data.get("confidence"),
                "pattern_type": signal_data.get("pattern_type"),
                "entry_price": str(signal_data.get("entry_price", "")),
                "stop_loss": str(signal_data.get("stop_loss", "")),
                "take_profit": str(signal_data.get("take_profit", ""))
            }
        )

    def log_disagreement_decision(self, decision_data: Dict[str, Any], account_id: str):
        """Log disagreement engine decision"""
        self.log_event(
            AuditEventType.DISAGREEMENT_DECISION,
            "disagreement_engine",
            f"Decision made for account {account_id}: {decision_data.get('decision', 'unknown')}",
            {
                "account_id": account_id,
                "decision": decision_data.get("decision"),
                "reasoning": decision_data.get("reasoning"),
                "modifications": decision_data.get("modifications", {}),
                "signal_id": decision_data.get("signal_id")
            },
            compliance_relevant=True
        )

    def log_trade_execution(self, trade_data: Dict[str, Any], execution_engine: str):
        """Log trade execution event"""
        self.log_event(
            AuditEventType.TRADE_EXECUTED,
            execution_engine,
            f"Trade executed: {trade_data.get('side', 'unknown')} {trade_data.get('symbol', 'unknown')}",
            {
                "trade_id": trade_data.get("trade_id"),
                "symbol": trade_data.get("symbol"),
                "side": trade_data.get("side"),
                "size": str(trade_data.get("size", "")),
                "entry_price": str(trade_data.get("entry_price", "")),
                "stop_loss": str(trade_data.get("stop_loss", "")),
                "take_profit": str(trade_data.get("take_profit", "")),
                "account_id": trade_data.get("account_id"),
                "signal_id": trade_data.get("signal_id")
            },
            risk_level="warning",  # All trades are important
            compliance_relevant=True
        )

    def log_random_usage_detected(self, violation_data: Dict[str, Any]):
        """Log random usage violation"""
        self.log_event(
            AuditEventType.RANDOM_USAGE_DETECTED,
            "production_validator",
            f"Random usage detected: {violation_data.get('file', 'unknown')}",
            violation_data,
            risk_level="critical",
            compliance_relevant=True
        )

    def log_system_config_change(self, config_change: Dict[str, Any], component: str):
        """Log system configuration change"""
        self.log_event(
            AuditEventType.SYSTEM_CONFIG_CHANGED,
            component,
            f"Configuration changed: {config_change.get('setting', 'unknown')}",
            config_change,
            risk_level="warning",
            compliance_relevant=True
        )

    async def get_events_by_type(self, event_type: AuditEventType, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events of a specific type"""
        events = []

        # Flush current buffer first
        await self.flush_events()

        # Read from current log file
        if self.current_log_file.exists():
            try:
                with open(self.current_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            if event_data.get('event_type') == event_type.value:
                                events.append(event_data)
                                if len(events) >= limit:
                                    break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error reading audit events: {e}")

        return events[-limit:]  # Return most recent events

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        total_events = sum(self.event_counts.values())

        return {
            "total_events": total_events,
            "events_by_type": self.event_counts.copy(),
            "buffer_size": len(self.event_buffer),
            "current_log_file": str(self.current_log_file),
            "log_directory": str(self.log_directory)
        }

    async def cleanup(self):
        """Clean up resources"""
        # Flush remaining events
        await self.flush_events()

        # Cancel flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger

    if _audit_logger is None:
        log_dir = os.getenv("AUDIT_LOG_DIR", "audit_logs")
        _audit_logger = AuditLogger(log_dir)

    return _audit_logger


def log_trading_event(event_type: AuditEventType, component: str, description: str, data: Dict[str, Any]):
    """Convenience function to log trading events"""
    audit_logger = get_audit_logger()
    return audit_logger.log_event(event_type, component, description, data)