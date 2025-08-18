"""
Audit Reporting System - Story 8.15

Provides comprehensive audit reporting including:
- On-demand audit reports
- Full trade details and audit trails
- Regulatory compliance reports
- System activity logs
- User action auditing
- Real-time audit data export
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
import csv
import hashlib
from pathlib import Path
from collections import defaultdict
import xml.etree.ElementTree as ET

logger = structlog.get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TRADE_EXECUTION = "trade_execution"
    ORDER_PLACEMENT = "order_placement"
    ORDER_MODIFICATION = "order_modification"
    ORDER_CANCELLATION = "order_cancellation"
    ACCOUNT_CREATION = "account_creation"
    ACCOUNT_MODIFICATION = "account_modification"
    FUND_DEPOSIT = "fund_deposit"
    FUND_WITHDRAWAL = "fund_withdrawal"
    SYSTEM_ACCESS = "system_access"
    DATA_EXPORT = "data_export"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_ACTION = "compliance_action"
    REGULATORY_FILING = "regulatory_filing"


class ReportType(Enum):
    """Types of audit reports"""
    TRADING_ACTIVITY = "trading_activity"
    USER_ACTIVITY = "user_activity"
    SYSTEM_ACTIVITY = "system_activity"
    COMPLIANCE_SUMMARY = "compliance_summary"
    REGULATORY_FILINGS = "regulatory_filings"
    SECURITY_EVENTS = "security_events"
    DATA_ACCESS = "data_access"
    FINANCIAL_TRANSACTIONS = "financial_transactions"
    PDT_VIOLATIONS = "pdt_violations"
    TAX_REPORTING = "tax_reporting"
    GDPR_COMPLIANCE = "gdpr_compliance"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FULL_AUDIT_TRAIL = "full_audit_trail"


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    PDF = "pdf"
    EXCEL = "excel"


class AuditLevel(Enum):
    """Audit event levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Individual audit event"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    account_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    event_data: Dict[str, Any]
    level: AuditLevel
    source_system: str
    correlation_id: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReportRequest:
    """Audit report request"""
    request_id: str
    report_type: ReportType
    start_date: datetime
    end_date: datetime
    filters: Dict[str, Any]
    output_format: ReportFormat
    requested_by: str
    request_timestamp: datetime
    priority: str = "normal"  # normal, high, urgent
    include_pii: bool = False
    encryption_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Generated audit report"""
    report_id: str
    request_id: str
    report_type: ReportType
    generation_timestamp: datetime
    period_start: datetime
    period_end: datetime
    total_events: int
    file_path: Optional[Path]
    file_size_bytes: int
    checksum: str
    encrypted: bool
    summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeAuditRecord:
    """Comprehensive trade audit record"""
    trade_id: str
    account_id: str
    user_id: str
    instrument: str
    trade_type: str  # buy, sell, short, cover
    quantity: Decimal
    price: Decimal
    execution_timestamp: datetime
    order_id: Optional[str]
    order_timestamp: Optional[datetime]
    venue: str
    commission: Decimal
    fees: Decimal
    settlement_date: date
    trade_status: str
    counterparty: Optional[str]
    clearing_member: Optional[str]
    regulatory_flags: List[str]
    compliance_checks: Dict[str, bool]
    risk_metrics: Dict[str, float]
    approval_chain: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditReportingSystem:
    """Main audit reporting system"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.audit_events: List[AuditEvent] = []
        self.report_requests: Dict[str, AuditReportRequest] = {}
        self.generated_reports: Dict[str, AuditReport] = {}
        self.trade_audit_records: Dict[str, TradeAuditRecord] = {}
        self.event_logger = EventLogger()
        self.report_generator = ReportGenerator(storage_path)
        self.data_exporter = DataExporter()
        self.compliance_aggregator = ComplianceAggregator()
        
    async def initialize(self):
        """Initialize audit reporting system"""
        logger.info("Initializing audit reporting system")
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "reports").mkdir(exist_ok=True)
        (self.storage_path / "exports").mkdir(exist_ok=True)
        (self.storage_path / "logs").mkdir(exist_ok=True)
        
        await self.event_logger.initialize()
        await self.report_generator.initialize()
        await self.data_exporter.initialize()
        await self.compliance_aggregator.initialize()
        
    async def log_audit_event(self, event_type: AuditEventType, user_id: Optional[str],
                             account_id: Optional[str], event_data: Dict[str, Any],
                             level: AuditLevel = AuditLevel.INFO,
                             session_id: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             user_agent: Optional[str] = None) -> AuditEvent:
        """Log an audit event"""
        
        # Create event
        event = AuditEvent(
            event_id=f"audit_{datetime.now().timestamp()}_{hashlib.md5(str(event_data).encode()).hexdigest()[:8]}",
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            account_id=account_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_data=event_data,
            level=level,
            source_system="trading_platform",
            correlation_id=event_data.get('correlation_id'),
            checksum=hashlib.sha256(json.dumps(event_data, sort_keys=True).encode()).hexdigest()
        )
        
        # Store event
        self.audit_events.append(event)
        
        # Log to persistent storage
        await self.event_logger.store_event(event)
        
        logger.info(f"Logged audit event: {event.event_id} - {event_type.value}")
        return event
        
    async def log_trade_execution(self, trade_data: Dict[str, Any]) -> TradeAuditRecord:
        """Log comprehensive trade execution audit record"""
        
        trade_record = TradeAuditRecord(
            trade_id=trade_data['trade_id'],
            account_id=trade_data['account_id'],
            user_id=trade_data.get('user_id', ''),
            instrument=trade_data['instrument'],
            trade_type=trade_data['trade_type'],
            quantity=Decimal(str(trade_data['quantity'])),
            price=Decimal(str(trade_data['price'])),
            execution_timestamp=datetime.fromisoformat(trade_data['timestamp']),
            order_id=trade_data.get('order_id'),
            order_timestamp=datetime.fromisoformat(trade_data['order_timestamp']) if trade_data.get('order_timestamp') else None,
            venue=trade_data.get('venue', 'primary'),
            commission=Decimal(str(trade_data.get('commission', 0))),
            fees=Decimal(str(trade_data.get('fees', 0))),
            settlement_date=datetime.fromisoformat(trade_data['settlement_date']).date() if trade_data.get('settlement_date') else date.today(),
            trade_status=trade_data.get('status', 'filled'),
            counterparty=trade_data.get('counterparty'),
            clearing_member=trade_data.get('clearing_member'),
            regulatory_flags=trade_data.get('regulatory_flags', []),
            compliance_checks=trade_data.get('compliance_checks', {}),
            risk_metrics=trade_data.get('risk_metrics', {}),
            approval_chain=trade_data.get('approval_chain', [])
        )
        
        self.trade_audit_records[trade_record.trade_id] = trade_record
        
        # Also log as audit event
        await self.log_audit_event(
            AuditEventType.TRADE_EXECUTION,
            trade_record.user_id,
            trade_record.account_id,
            {
                'trade_id': trade_record.trade_id,
                'instrument': trade_record.instrument,
                'quantity': float(trade_record.quantity),
                'price': float(trade_record.price),
                'venue': trade_record.venue
            }
        )
        
        return trade_record
        
    async def request_audit_report(self, report_type: ReportType, start_date: datetime,
                                  end_date: datetime, filters: Dict[str, Any],
                                  output_format: ReportFormat, requested_by: str,
                                  include_pii: bool = False) -> AuditReportRequest:
        """Request an audit report"""
        
        request = AuditReportRequest(
            request_id=f"req_{datetime.now().timestamp()}",
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            output_format=output_format,
            requested_by=requested_by,
            request_timestamp=datetime.now(),
            include_pii=include_pii,
            encryption_required=True
        )
        
        self.report_requests[request.request_id] = request
        
        # Log the report request
        await self.log_audit_event(
            AuditEventType.DATA_EXPORT,
            requested_by,
            None,
            {
                'request_id': request.request_id,
                'report_type': report_type.value,
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'format': output_format.value
            }
        )
        
        logger.info(f"Audit report requested: {request.request_id}")
        return request
        
    async def generate_audit_report(self, request_id: str) -> AuditReport:
        """Generate audit report from request"""
        
        if request_id not in self.report_requests:
            raise ValueError(f"Report request not found: {request_id}")
        
        request = self.report_requests[request_id]
        
        # Generate report based on type
        report_data = await self._generate_report_data(request)
        
        # Create report file
        report_file = await self.report_generator.create_report_file(
            request, report_data
        )
        
        # Calculate checksum
        checksum = await self._calculate_file_checksum(report_file)
        
        # Create report record
        report = AuditReport(
            report_id=f"rpt_{request.request_id}",
            request_id=request_id,
            report_type=request.report_type,
            generation_timestamp=datetime.now(),
            period_start=request.start_date,
            period_end=request.end_date,
            total_events=len(report_data),
            file_path=report_file,
            file_size_bytes=report_file.stat().st_size,
            checksum=checksum,
            encrypted=request.encryption_required,
            summary=await self._generate_report_summary(report_data, request.report_type)
        )
        
        self.generated_reports[report.report_id] = report
        
        logger.info(f"Generated audit report: {report.report_id}")
        return report
        
    async def _generate_report_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Generate report data based on request"""
        
        if request.report_type == ReportType.TRADING_ACTIVITY:
            return await self._get_trading_activity_data(request)
        elif request.report_type == ReportType.USER_ACTIVITY:
            return await self._get_user_activity_data(request)
        elif request.report_type == ReportType.SYSTEM_ACTIVITY:
            return await self._get_system_activity_data(request)
        elif request.report_type == ReportType.COMPLIANCE_SUMMARY:
            return await self._get_compliance_summary_data(request)
        elif request.report_type == ReportType.FULL_AUDIT_TRAIL:
            return await self._get_full_audit_trail_data(request)
        else:
            return await self._get_filtered_events(request)
            
    async def _get_trading_activity_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get trading activity data"""
        data = []
        
        for trade_record in self.trade_audit_records.values():
            if request.start_date <= trade_record.execution_timestamp <= request.end_date:
                # Apply filters
                if self._matches_filters(trade_record, request.filters):
                    trade_data = {
                        'trade_id': trade_record.trade_id,
                        'account_id': trade_record.account_id,
                        'instrument': trade_record.instrument,
                        'trade_type': trade_record.trade_type,
                        'quantity': float(trade_record.quantity),
                        'price': float(trade_record.price),
                        'execution_time': trade_record.execution_timestamp.isoformat(),
                        'venue': trade_record.venue,
                        'commission': float(trade_record.commission),
                        'fees': float(trade_record.fees),
                        'settlement_date': trade_record.settlement_date.isoformat(),
                        'status': trade_record.trade_status
                    }
                    
                    # Include PII only if requested and authorized
                    if request.include_pii:
                        trade_data['user_id'] = trade_record.user_id
                        trade_data['counterparty'] = trade_record.counterparty
                    
                    data.append(trade_data)
        
        return data
        
    async def _get_user_activity_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get user activity data"""
        data = []
        
        user_events = [
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGOUT,
            AuditEventType.ORDER_PLACEMENT,
            AuditEventType.ORDER_MODIFICATION,
            AuditEventType.ORDER_CANCELLATION
        ]
        
        for event in self.audit_events:
            if (event.event_type in user_events and
                request.start_date <= event.timestamp <= request.end_date):
                
                if self._matches_filters(event, request.filters):
                    event_data = {
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'account_id': event.account_id,
                        'session_id': event.session_id,
                        'ip_address': event.ip_address,
                        'event_details': event.event_data
                    }
                    
                    if request.include_pii:
                        event_data['user_id'] = event.user_id
                        event_data['user_agent'] = event.user_agent
                    
                    data.append(event_data)
        
        return data
        
    async def _get_system_activity_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get system activity data"""
        data = []
        
        system_events = [
            AuditEventType.SYSTEM_ACCESS,
            AuditEventType.CONFIGURATION_CHANGE,
            AuditEventType.SECURITY_EVENT
        ]
        
        for event in self.audit_events:
            if (event.event_type in system_events and
                request.start_date <= event.timestamp <= request.end_date):
                
                if self._matches_filters(event, request.filters):
                    data.append({
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'level': event.level.value,
                        'source_system': event.source_system,
                        'event_details': event.event_data
                    })
        
        return data
        
    async def _get_compliance_summary_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get compliance summary data"""
        return await self.compliance_aggregator.generate_compliance_summary(
            request.start_date, request.end_date
        )
        
    async def _get_full_audit_trail_data(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get full audit trail data"""
        data = []
        
        for event in self.audit_events:
            if request.start_date <= event.timestamp <= request.end_date:
                if self._matches_filters(event, request.filters):
                    event_data = {
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'level': event.level.value,
                        'source_system': event.source_system,
                        'checksum': event.checksum,
                        'event_details': event.event_data
                    }
                    
                    if request.include_pii:
                        event_data['user_id'] = event.user_id
                        event_data['account_id'] = event.account_id
                        event_data['session_id'] = event.session_id
                        event_data['ip_address'] = event.ip_address
                        event_data['user_agent'] = event.user_agent
                    
                    data.append(event_data)
        
        return data
        
    async def _get_filtered_events(self, request: AuditReportRequest) -> List[Dict[str, Any]]:
        """Get filtered events based on request"""
        data = []
        
        for event in self.audit_events:
            if request.start_date <= event.timestamp <= request.end_date:
                if self._matches_filters(event, request.filters):
                    data.append({
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'event_details': event.event_data
                    })
        
        return data
        
    def _matches_filters(self, record: Union[AuditEvent, TradeAuditRecord], 
                        filters: Dict[str, Any]) -> bool:
        """Check if record matches filters"""
        if not filters:
            return True
        
        # Apply various filters
        if 'account_id' in filters:
            if hasattr(record, 'account_id') and record.account_id != filters['account_id']:
                return False
        
        if 'user_id' in filters:
            if hasattr(record, 'user_id') and record.user_id != filters['user_id']:
                return False
        
        if 'instrument' in filters:
            if hasattr(record, 'instrument') and record.instrument != filters['instrument']:
                return False
        
        if 'event_type' in filters:
            if hasattr(record, 'event_type') and record.event_type.value != filters['event_type']:
                return False
        
        return True
        
    async def _generate_report_summary(self, data: List[Dict[str, Any]], 
                                      report_type: ReportType) -> Dict[str, Any]:
        """Generate summary for report"""
        summary = {
            'total_records': len(data),
            'generation_time': datetime.now().isoformat(),
            'report_type': report_type.value
        }
        
        if report_type == ReportType.TRADING_ACTIVITY:
            instruments = set()
            total_volume = Decimal('0')
            
            for record in data:
                instruments.add(record.get('instrument', ''))
                volume = Decimal(str(record.get('quantity', 0))) * Decimal(str(record.get('price', 0)))
                total_volume += volume
            
            summary.update({
                'unique_instruments': len(instruments),
                'total_volume': float(total_volume),
                'instruments': list(instruments)
            })
        
        return summary
        
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate checksum for file"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
        
    async def get_audit_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get audit summary for period"""
        period_events = [
            event for event in self.audit_events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Count by event type
        event_counts = defaultdict(int)
        level_counts = defaultdict(int)
        
        for event in period_events:
            event_counts[event.event_type.value] += 1
            level_counts[event.level.value] += 1
        
        # Trading summary
        period_trades = [
            trade for trade in self.trade_audit_records.values()
            if start_date <= trade.execution_timestamp <= end_date
        ]
        
        return {
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'total_events': len(period_events),
            'events_by_type': dict(event_counts),
            'events_by_level': dict(level_counts),
            'total_trades': len(period_trades),
            'unique_accounts': len(set(event.account_id for event in period_events if event.account_id)),
            'unique_users': len(set(event.user_id for event in period_events if event.user_id)),
            'generated_reports': len(self.generated_reports),
            'pending_requests': len([r for r in self.report_requests.values() 
                                   if r.request_timestamp >= start_date])
        }


class EventLogger:
    """Logs audit events to persistent storage"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize event logger"""
        logger.info("Initialized event logger")
        
    async def store_event(self, event: AuditEvent):
        """Store event to persistent storage"""
        # In production, this would store to database or log files
        logger.debug(f"Stored audit event: {event.event_id}")


class ReportGenerator:
    """Generates audit reports in various formats"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        
    async def initialize(self):
        """Initialize report generator"""
        logger.info("Initialized report generator")
        
    async def create_report_file(self, request: AuditReportRequest, 
                                data: List[Dict[str, Any]]) -> Path:
        """Create report file in requested format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{request.report_type.value}_{timestamp}"
        
        if request.output_format == ReportFormat.JSON:
            return await self._create_json_report(filename, data)
        elif request.output_format == ReportFormat.CSV:
            return await self._create_csv_report(filename, data)
        elif request.output_format == ReportFormat.XML:
            return await self._create_xml_report(filename, data)
        else:
            # Default to JSON
            return await self._create_json_report(filename, data)
            
    async def _create_json_report(self, filename: str, data: List[Dict[str, Any]]) -> Path:
        """Create JSON format report"""
        file_path = self.storage_path / "reports" / f"{filename}.json"
        
        with open(file_path, 'w') as f:
            json.dump({
                'metadata': {
                    'generation_time': datetime.now().isoformat(),
                    'record_count': len(data)
                },
                'data': data
            }, f, indent=2)
        
        return file_path
        
    async def _create_csv_report(self, filename: str, data: List[Dict[str, Any]]) -> Path:
        """Create CSV format report"""
        file_path = self.storage_path / "reports" / f"{filename}.csv"
        
        if not data:
            # Create empty file
            with open(file_path, 'w') as f:
                f.write("No data available\n")
            return file_path
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return file_path
        
    async def _create_xml_report(self, filename: str, data: List[Dict[str, Any]]) -> Path:
        """Create XML format report"""
        file_path = self.storage_path / "reports" / f"{filename}.xml"
        
        root = ET.Element("audit_report")
        
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "generation_time").text = datetime.now().isoformat()
        ET.SubElement(metadata, "record_count").text = str(len(data))
        
        records = ET.SubElement(root, "records")
        
        for record in data:
            record_elem = ET.SubElement(records, "record")
            for key, value in record.items():
                elem = ET.SubElement(record_elem, key)
                elem.text = str(value) if value is not None else ""
        
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
        return file_path


class DataExporter:
    """Exports audit data for external systems"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize data exporter"""
        logger.info("Initialized data exporter")
        
    async def export_real_time_data(self, event: AuditEvent) -> Dict[str, Any]:
        """Export real-time audit data"""
        return {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'type': event.event_type.value,
            'level': event.level.value,
            'data': event.event_data
        }


class ComplianceAggregator:
    """Aggregates compliance-related audit data"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize compliance aggregator"""
        logger.info("Initialized compliance aggregator")
        
    async def generate_compliance_summary(self, start_date: datetime, 
                                         end_date: datetime) -> List[Dict[str, Any]]:
        """Generate compliance summary for period"""
        # This would aggregate various compliance metrics
        return [
            {
                'metric': 'pdt_violations',
                'count': 0,
                'description': 'Pattern Day Trading violations'
            },
            {
                'metric': 'large_trader_reports',
                'count': 0,
                'description': 'Large trader reports filed'
            },
            {
                'metric': 'suspicious_activities',
                'count': 0,
                'description': 'Suspicious activities detected'
            },
            {
                'metric': 'gdpr_requests',
                'count': 0,
                'description': 'GDPR data subject requests'
            }
        ]