"""
Audit Trail System
Story 8.8 - Task 5: Build audit trail system
"""
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import json
import uuid

try:
    from .transaction_manager import TransactionRecord, OandaTransactionManager
except ImportError:
    from transaction_manager import TransactionRecord, OandaTransactionManager

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SIGNAL_EXECUTED = "SIGNAL_EXECUTED"
    TRADE_OPENED = "TRADE_OPENED"
    TRADE_CLOSED = "TRADE_CLOSED"
    RISK_CHECK = "RISK_CHECK"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    SYSTEM_ACTION = "SYSTEM_ACTION"
    USER_ACTION = "USER_ACTION"


@dataclass
class AuditRecord:
    """Represents an audit trail record"""
    audit_id: str
    event_type: AuditEventType
    timestamp: datetime
    account_id: str
    signal_id: Optional[str] = None
    transaction_id: Optional[str] = None
    trade_id: Optional[str] = None
    order_id: Optional[str] = None
    user_id: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    source_component: Optional[str] = None
    risk_score: Optional[float] = None
    compliance_status: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['event_type'] = self.event_type.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class SignalExecutionTrail:
    """Complete trail from signal to execution"""
    signal_id: str
    signal_timestamp: datetime
    execution_timestamp: Optional[datetime]
    transaction_ids: List[str]
    risk_checks: List[AuditRecord]
    compliance_checks: List[AuditRecord]
    execution_latency_ms: Optional[float]
    execution_success: bool
    failure_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'signal_id': self.signal_id,
            'signal_timestamp': self.signal_timestamp.isoformat(),
            'execution_timestamp': self.execution_timestamp.isoformat() if self.execution_timestamp else None,
            'transaction_ids': self.transaction_ids,
            'risk_checks': [r.to_dict() for r in self.risk_checks],
            'compliance_checks': [c.to_dict() for c in self.compliance_checks],
            'execution_latency_ms': self.execution_latency_ms,
            'execution_success': self.execution_success,
            'failure_reason': self.failure_reason
        }


@dataclass
class AuditReport:
    """Comprehensive audit report"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    account_ids: List[str]
    total_signals: int
    executed_signals: int
    failed_signals: int
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    audit_coverage: float
    signal_execution_trails: List[SignalExecutionTrail]
    compliance_violations: List[AuditRecord]
    risk_events: List[AuditRecord]
    system_anomalies: List[AuditRecord]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'account_ids': self.account_ids,
            'total_signals': self.total_signals,
            'executed_signals': self.executed_signals,
            'failed_signals': self.failed_signals,
            'total_transactions': self.total_transactions,
            'matched_transactions': self.matched_transactions,
            'unmatched_transactions': self.unmatched_transactions,
            'audit_coverage': self.audit_coverage,
            'signal_execution_trails': [s.to_dict() for s in self.signal_execution_trails],
            'compliance_violations': [c.to_dict() for c in self.compliance_violations],
            'risk_events': [r.to_dict() for r in self.risk_events],
            'system_anomalies': [a.to_dict() for a in self.system_anomalies]
        }


class AuditTrailManager:
    """Manages audit trail for trading signals and transactions"""
    
    def __init__(self, transaction_manager: Optional[OandaTransactionManager] = None):
        self.transaction_manager = transaction_manager
        self.audit_records: Dict[str, AuditRecord] = {}
        self.signal_mappings: Dict[str, str] = {}  # transaction_id -> signal_id
        self.execution_trails: Dict[str, SignalExecutionTrail] = {}
        self.retention_days = 2555  # 7 years retention
        
    async def record_signal_generated(self,
                                    signal_id: str,
                                    account_id: str,
                                    signal_data: Dict[str, Any],
                                    correlation_id: Optional[str] = None) -> str:
        """
        Record when a trading signal is generated
        
        Args:
            signal_id: Unique signal identifier
            account_id: Account the signal is for
            signal_data: Signal parameters and metadata
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Audit record ID
        """
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            event_type=AuditEventType.SIGNAL_GENERATED,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            signal_id=signal_id,
            event_data=signal_data,
            correlation_id=correlation_id,
            source_component="signal_generator"
        )
        
        self.audit_records[audit_id] = audit_record
        
        # Initialize execution trail
        self.execution_trails[signal_id] = SignalExecutionTrail(
            signal_id=signal_id,
            signal_timestamp=audit_record.timestamp,
            execution_timestamp=None,
            transaction_ids=[],
            risk_checks=[],
            compliance_checks=[],
            execution_latency_ms=None,
            execution_success=False
        )
        
        logger.info(f"Recorded signal generation: {signal_id}")
        return audit_id
        
    async def record_risk_check(self,
                              signal_id: str,
                              account_id: str,
                              risk_data: Dict[str, Any],
                              risk_score: float,
                              passed: bool,
                              correlation_id: Optional[str] = None) -> str:
        """
        Record risk check for a signal
        
        Args:
            signal_id: Signal being checked
            account_id: Account ID
            risk_data: Risk assessment data
            risk_score: Calculated risk score
            passed: Whether risk check passed
            correlation_id: Optional correlation ID
            
        Returns:
            Audit record ID
        """
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            event_type=AuditEventType.RISK_CHECK,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            signal_id=signal_id,
            event_data=risk_data,
            correlation_id=correlation_id,
            source_component="risk_manager",
            risk_score=risk_score,
            notes=f"Risk check {'PASSED' if passed else 'FAILED'}"
        )
        
        self.audit_records[audit_id] = audit_record
        
        # Add to execution trail
        if signal_id in self.execution_trails:
            self.execution_trails[signal_id].risk_checks.append(audit_record)
            
        logger.info(f"Recorded risk check for signal {signal_id}: {'PASSED' if passed else 'FAILED'}")
        return audit_id
        
    async def record_compliance_check(self,
                                    signal_id: str,
                                    account_id: str,
                                    compliance_data: Dict[str, Any],
                                    status: str,
                                    correlation_id: Optional[str] = None) -> str:
        """
        Record compliance check for a signal
        
        Args:
            signal_id: Signal being checked
            account_id: Account ID
            compliance_data: Compliance check data
            status: Compliance status (PASSED, FAILED, WARNING)
            correlation_id: Optional correlation ID
            
        Returns:
            Audit record ID
        """
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            event_type=AuditEventType.COMPLIANCE_CHECK,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            signal_id=signal_id,
            event_data=compliance_data,
            correlation_id=correlation_id,
            source_component="compliance_engine",
            compliance_status=status,
            notes=f"Compliance check: {status}"
        )
        
        self.audit_records[audit_id] = audit_record
        
        # Add to execution trail
        if signal_id in self.execution_trails:
            self.execution_trails[signal_id].compliance_checks.append(audit_record)
            
        logger.info(f"Recorded compliance check for signal {signal_id}: {status}")
        return audit_id
        
    async def link_signal_to_transaction(self,
                                       signal_id: str,
                                       transaction_id: str,
                                       account_id: str,
                                       execution_latency_ms: Optional[float] = None,
                                       correlation_id: Optional[str] = None) -> str:
        """
        Link a trading signal to its resulting transaction
        
        Args:
            signal_id: Original signal ID
            transaction_id: OANDA transaction ID
            account_id: Account ID
            execution_latency_ms: Time from signal to execution
            correlation_id: Optional correlation ID
            
        Returns:
            Audit record ID
        """
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            event_type=AuditEventType.SIGNAL_EXECUTED,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            signal_id=signal_id,
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            source_component="execution_engine",
            event_data={
                'execution_latency_ms': execution_latency_ms,
                'signal_to_transaction_mapping': True
            }
        )
        
        self.audit_records[audit_id] = audit_record
        self.signal_mappings[transaction_id] = signal_id
        
        # Update execution trail
        if signal_id in self.execution_trails:
            trail = self.execution_trails[signal_id]
            trail.execution_timestamp = audit_record.timestamp
            trail.transaction_ids.append(transaction_id)
            trail.execution_latency_ms = execution_latency_ms
            trail.execution_success = True
            
        logger.info(f"Linked signal {signal_id} to transaction {transaction_id}")
        return audit_id
        
    async def record_trade_event(self,
                               transaction_id: str,
                               account_id: str,
                               event_type: AuditEventType,
                               trade_data: Dict[str, Any],
                               correlation_id: Optional[str] = None) -> str:
        """
        Record trade-related events (open/close)
        
        Args:
            transaction_id: Transaction ID
            account_id: Account ID
            event_type: Type of trade event
            trade_data: Trade event data
            correlation_id: Optional correlation ID
            
        Returns:
            Audit record ID
        """
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            account_id=account_id,
            transaction_id=transaction_id,
            trade_id=trade_data.get('trade_id'),
            order_id=trade_data.get('order_id'),
            event_data=trade_data,
            correlation_id=correlation_id,
            source_component="trade_manager"
        )
        
        self.audit_records[audit_id] = audit_record
        logger.info(f"Recorded trade event: {event_type.value} for transaction {transaction_id}")
        return audit_id
        
    async def get_signal_execution_trail(self, signal_id: str) -> Optional[SignalExecutionTrail]:
        """Get complete execution trail for a signal"""
        return self.execution_trails.get(signal_id)
        
    async def get_transaction_audit_trail(self, transaction_id: str) -> List[AuditRecord]:
        """Get all audit records related to a transaction"""
        return [
            record for record in self.audit_records.values()
            if record.transaction_id == transaction_id
        ]
        
    async def generate_audit_report(self,
                                  start_date: datetime,
                                  end_date: datetime,
                                  account_ids: Optional[List[str]] = None) -> AuditReport:
        """
        Generate comprehensive audit report
        
        Args:
            start_date: Report period start
            end_date: Report period end
            account_ids: Optional list of account IDs to include
            
        Returns:
            AuditReport object
        """
        report_id = str(uuid.uuid4())
        
        # Filter records by date and accounts
        period_records = [
            record for record in self.audit_records.values()
            if start_date <= record.timestamp <= end_date
            and (not account_ids or record.account_id in account_ids)
        ]
        
        # Get transactions for the period
        transactions = []
        if self.transaction_manager and account_ids:
            for account_id in account_ids:
                try:
                    result = await self.transaction_manager.get_transaction_history(
                        account_id, start_date, end_date
                    )
                    transactions.extend(result.get('transactions', []))
                except Exception as e:
                    logger.error(f"Failed to get transactions for {account_id}: {e}")
                    
        # Analyze signals
        signal_records = [r for r in period_records if r.event_type == AuditEventType.SIGNAL_GENERATED]
        executed_records = [r for r in period_records if r.event_type == AuditEventType.SIGNAL_EXECUTED]
        
        total_signals = len(signal_records)
        executed_signals = len(executed_records)
        failed_signals = total_signals - executed_signals
        
        # Analyze transaction matching
        total_transactions = len(transactions)
        matched_transactions = len([t for t in transactions if t.transaction_id in self.signal_mappings])
        unmatched_transactions = total_transactions - matched_transactions
        
        audit_coverage = (matched_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        # Get execution trails for the period
        period_trails = [
            trail for trail in self.execution_trails.values()
            if start_date <= trail.signal_timestamp <= end_date
        ]
        
        # Identify compliance violations and risk events
        compliance_violations = [
            r for r in period_records 
            if r.event_type == AuditEventType.COMPLIANCE_CHECK 
            and r.compliance_status in ['FAILED', 'VIOLATION']
        ]
        
        risk_events = [
            r for r in period_records 
            if r.event_type == AuditEventType.RISK_CHECK 
            and r.risk_score and r.risk_score > 80  # High risk threshold
        ]
        
        # Identify system anomalies (execution latency, failures, etc.)
        system_anomalies = self._identify_system_anomalies(period_records, period_trails)
        
        return AuditReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            period_start=start_date,
            period_end=end_date,
            account_ids=account_ids or [],
            total_signals=total_signals,
            executed_signals=executed_signals,
            failed_signals=failed_signals,
            total_transactions=total_transactions,
            matched_transactions=matched_transactions,
            unmatched_transactions=unmatched_transactions,
            audit_coverage=audit_coverage,
            signal_execution_trails=period_trails,
            compliance_violations=compliance_violations,
            risk_events=risk_events,
            system_anomalies=system_anomalies
        )
        
    def _identify_system_anomalies(self,
                                 records: List[AuditRecord],
                                 trails: List[SignalExecutionTrail]) -> List[AuditRecord]:
        """Identify system anomalies from audit data"""
        anomalies = []
        
        # High latency executions (>5 seconds)
        high_latency_trails = [
            t for t in trails 
            if t.execution_latency_ms and t.execution_latency_ms > 5000
        ]
        
        for trail in high_latency_trails:
            anomaly = AuditRecord(
                audit_id=str(uuid.uuid4()),
                event_type=AuditEventType.SYSTEM_ACTION,
                timestamp=trail.execution_timestamp or trail.signal_timestamp,
                account_id="",  # Will be set from signal data
                signal_id=trail.signal_id,
                event_data={'anomaly_type': 'HIGH_LATENCY', 'latency_ms': trail.execution_latency_ms},
                source_component="audit_system",
                notes=f"High execution latency: {trail.execution_latency_ms}ms"
            )
            anomalies.append(anomaly)
            
        # Failed executions
        failed_trails = [t for t in trails if not t.execution_success]
        for trail in failed_trails:
            anomaly = AuditRecord(
                audit_id=str(uuid.uuid4()),
                event_type=AuditEventType.SYSTEM_ACTION,
                timestamp=trail.signal_timestamp,
                account_id="",
                signal_id=trail.signal_id,
                event_data={'anomaly_type': 'EXECUTION_FAILURE', 'reason': trail.failure_reason},
                source_component="audit_system",
                notes=f"Execution failure: {trail.failure_reason}"
            )
            anomalies.append(anomaly)
            
        return anomalies
        
    async def cleanup_old_records(self):
        """Remove audit records older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Remove old audit records
        old_records = [
            audit_id for audit_id, record in self.audit_records.items()
            if record.timestamp < cutoff_date
        ]
        
        for audit_id in old_records:
            del self.audit_records[audit_id]
            
        # Remove old execution trails
        old_trails = [
            signal_id for signal_id, trail in self.execution_trails.items()
            if trail.signal_timestamp < cutoff_date
        ]
        
        for signal_id in old_trails:
            del self.execution_trails[signal_id]
            
        logger.info(f"Cleaned up {len(old_records)} old audit records and {len(old_trails)} old trails")
        
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics"""
        total_records = len(self.audit_records)
        total_trails = len(self.execution_trails)
        
        # Count by event type
        event_counts = {}
        for record in self.audit_records.values():
            event_type = record.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        return {
            'total_audit_records': total_records,
            'total_execution_trails': total_trails,
            'event_type_counts': event_counts,
            'signal_mappings': len(self.signal_mappings)
        }