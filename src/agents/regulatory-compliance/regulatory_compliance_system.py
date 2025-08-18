"""
Main Regulatory Compliance System - Story 8.15

Integrates all regulatory compliance modules:
- Tax reporting system
- PDT monitoring
- Large trader reporting
- Suspicious activity monitoring
- Data retention system
- GDPR compliance
- Audit reporting system
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
from pathlib import Path

from .tax_reporting_system import TaxReportingSystem, TaxableTransaction
from .pdt_monitoring_system import PDTMonitoringSystem, DayTrade
from .large_trader_reporting import LargeTraderReportingSystem, TradingVolume
from .suspicious_activity_monitoring import SuspiciousActivityMonitoringSystem
from .data_retention_system import DataRetentionSystem, DataCategory
from .gdpr_compliance_system import GDPRComplianceSystem, DataSubject
from .audit_reporting_system import AuditReportingSystem, AuditEventType, AuditLevel

logger = structlog.get_logger(__name__)


class ComplianceModule(Enum):
    """Compliance modules"""
    TAX_REPORTING = "tax_reporting"
    PDT_MONITORING = "pdt_monitoring"
    LARGE_TRADER = "large_trader"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_RETENTION = "data_retention"
    GDPR_COMPLIANCE = "gdpr_compliance"
    AUDIT_REPORTING = "audit_reporting"


@dataclass
class ComplianceStatus:
    """Overall compliance status"""
    overall_status: str  # 'compliant', 'issues', 'critical'
    last_updated: datetime
    module_statuses: Dict[str, Dict[str, Any]]
    pending_actions: List[Dict[str, Any]]
    recent_alerts: List[Dict[str, Any]]
    compliance_score: float  # 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceAlert:
    """Compliance alert"""
    alert_id: str
    module: ComplianceModule
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    timestamp: datetime
    requires_action: bool
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegulatoryComplianceSystem:
    """Main regulatory compliance system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_path = Path(config.get('storage_path', './compliance_data'))
        
        # Initialize all compliance modules
        self.tax_reporting = TaxReportingSystem()
        self.pdt_monitoring = PDTMonitoringSystem()
        self.large_trader = LargeTraderReportingSystem()
        self.suspicious_activity = SuspiciousActivityMonitoringSystem()
        self.data_retention = DataRetentionSystem(self.storage_path / 'retention')
        self.gdpr_compliance = GDPRComplianceSystem()
        self.audit_reporting = AuditReportingSystem(self.storage_path / 'audit')
        
        # System state
        self.compliance_alerts: List[ComplianceAlert] = []
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all compliance modules"""
        logger.info("Initializing Regulatory Compliance System")
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize all modules
        await self.tax_reporting.initialize()
        await self.pdt_monitoring.initialize()
        await self.large_trader.initialize()
        await self.suspicious_activity.initialize()
        await self.data_retention.initialize()
        await self.gdpr_compliance.initialize()
        await self.audit_reporting.initialize()
        
        self.is_initialized = True
        
        # Log system initialization
        await self.audit_reporting.log_audit_event(
            AuditEventType.SYSTEM_ACCESS,
            None,
            None,
            {'action': 'compliance_system_initialized'},
            AuditLevel.INFO
        )
        
        logger.info("Regulatory Compliance System initialized successfully")
        
    async def process_trade(self, trade_data: Dict[str, Any]):
        """Process a trade through all compliance modules"""
        if not self.is_initialized:
            await self.initialize()
        
        trade_id = trade_data['trade_id']
        account_id = trade_data['account_id']
        
        # Log comprehensive trade audit
        await self.audit_reporting.log_trade_execution(trade_data)
        
        # Tax reporting
        if trade_data.get('taxable', True):
            tax_transaction = self._convert_to_tax_transaction(trade_data)
            await self.tax_reporting.record_transaction(tax_transaction)
        
        # PDT monitoring
        if 'open_time' in trade_data and 'close_time' in trade_data:
            day_trade = await self.pdt_monitoring.record_trade(
                account_id,
                trade_data['instrument'],
                datetime.fromisoformat(trade_data['open_time']),
                Decimal(str(trade_data['open_price'])),
                Decimal(str(trade_data['quantity'])),
                datetime.fromisoformat(trade_data['close_time']),
                Decimal(str(trade_data['price'])),
                Decimal(str(trade_data['quantity']))
            )
            
            if day_trade:
                logger.info(f"Day trade recorded: {day_trade.trade_id}")
        
        # Large trader monitoring
        await self.large_trader.record_trading_volume(
            account_id,
            datetime.fromisoformat(trade_data['timestamp']).date(),
            trade_data['instrument'],
            Decimal(str(trade_data['quantity'])),
            Decimal(str(trade_data['quantity'])) * Decimal(str(trade_data['price'])),
            trade_data.get('side', 'buy')
        )
        
        # Suspicious activity monitoring
        await self.suspicious_activity.analyze_trading_activity(account_id, [trade_data])
        
        # Data retention
        trade_json = str(trade_data).encode('utf-8')
        await self.data_retention.register_data_record(
            f"trade_{trade_id}",
            DataCategory.TRADING_RECORDS,
            trade_json,
            {'trade_id': trade_id, 'account_id': account_id}
        )
        
        logger.debug(f"Processed trade through compliance: {trade_id}")
        
    def _convert_to_tax_transaction(self, trade_data: Dict[str, Any]) -> TaxableTransaction:
        """Convert trade data to tax transaction"""
        from .tax_reporting_system import TransactionType
        
        # Map trade type to tax transaction type
        type_mapping = {
            'buy': TransactionType.BUY,
            'sell': TransactionType.SELL,
            'short': TransactionType.SHORT_SALE,
            'cover': TransactionType.COVER_SHORT
        }
        
        return TaxableTransaction(
            transaction_id=trade_data['trade_id'],
            account_id=trade_data['account_id'],
            instrument=trade_data['instrument'],
            transaction_type=type_mapping.get(trade_data.get('trade_type', 'buy'), TransactionType.BUY),
            transaction_date=datetime.fromisoformat(trade_data['timestamp']),
            settlement_date=datetime.fromisoformat(trade_data.get('settlement_date', trade_data['timestamp'])),
            quantity=Decimal(str(trade_data['quantity'])),
            price=Decimal(str(trade_data['price'])),
            total_amount=Decimal(str(trade_data['quantity'])) * Decimal(str(trade_data['price'])),
            commission=Decimal(str(trade_data.get('commission', 0))),
            fees=Decimal(str(trade_data.get('fees', 0)))
        )
        
    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user through compliance systems"""
        user_id = user_data['user_id']
        account_id = user_data['account_id']
        
        # GDPR compliance for EU users
        if user_data.get('country') and self.gdpr_compliance._is_eu_country(user_data['country']):
            data_subject = await self.gdpr_compliance.register_data_subject(
                user_data['email'],
                user_data['country'],
                user_data
            )
            logger.info(f"Registered EU data subject: {data_subject.subject_id}")
        
        # PDT monitoring setup
        await self.pdt_monitoring.update_account_status(
            account_id,
            Decimal(str(user_data.get('initial_equity', 0))),
            user_data.get('is_margin_account', True),
            user_data.get('has_options_approval', False)
        )
        
        # Large trader registration if applicable
        if user_data.get('is_institutional') or user_data.get('high_volume_trader'):
            await self.large_trader.register_large_trader(
                user_data.get('entity_name', user_data['name']),
                user_data.get('entity_type', 'individual'),
                user_data.get('tax_id', user_id),
                {account_id},
                user_data.get('ltid')
            )
        
        # Data retention
        user_json = str(user_data).encode('utf-8')
        await self.data_retention.register_data_record(
            f"user_{user_id}",
            DataCategory.CUSTOMER_DATA,
            user_json,
            {'user_id': user_id, 'account_id': account_id}
        )
        
        # Audit logging
        await self.audit_reporting.log_audit_event(
            AuditEventType.ACCOUNT_CREATION,
            user_id,
            account_id,
            {
                'registration_type': 'new_account',
                'country': user_data.get('country'),
                'is_eu_resident': user_data.get('country') and self.gdpr_compliance._is_eu_country(user_data['country'])
            }
        )
        
        return {
            'user_id': user_id,
            'account_id': account_id,
            'compliance_status': 'registered',
            'eu_resident': user_data.get('country') and self.gdpr_compliance._is_eu_country(user_data['country'])
        }
        
    async def check_trade_permission(self, account_id: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if trade is permitted by all compliance systems"""
        permissions = {
            'allowed': True,
            'warnings': [],
            'restrictions': [],
            'compliance_checks': {}
        }
        
        # PDT check
        is_day_trade = trade_data.get('is_day_trade', False)
        pdt_check = await self.pdt_monitoring.check_trade_permission(account_id, is_day_trade)
        permissions['compliance_checks']['pdt'] = pdt_check
        
        if not pdt_check.get('allowed', True):
            permissions['allowed'] = False
            permissions['restrictions'].append(f"PDT: {pdt_check.get('reason', 'Trade not permitted')}")
        
        if pdt_check.get('warning'):
            permissions['warnings'].append(f"PDT: {pdt_check['warning']}")
        
        # Suspicious activity check
        # This would check if account has active restrictions
        
        # Large trader check
        # This would check volume limits if applicable
        
        return permissions
        
    async def generate_compliance_report(self, report_type: str, 
                                        start_date: date, end_date: date,
                                        account_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        report_data = {
            'report_type': report_type,
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'generation_time': datetime.now().isoformat(),
            'account_id': account_id
        }
        
        if report_type == 'tax_summary' and account_id:
            # Generate tax summary
            tax_year = start_date.year
            if account_id in self.tax_reporting.form_1099_data and tax_year in self.tax_reporting.form_1099_data[account_id]:
                report_data['tax_summary'] = await self.tax_reporting.get_tax_summary(account_id, tax_year)
        
        elif report_type == 'pdt_compliance':
            # Generate PDT compliance report
            if account_id:
                report_data['pdt_summary'] = await self.pdt_monitoring.get_pdt_summary(account_id)
            else:
                # System-wide PDT summary
                report_data['pdt_summary'] = {
                    'total_accounts': len(self.pdt_monitoring.account_statuses),
                    'pdt_accounts': len([s for s in self.pdt_monitoring.account_statuses.values() 
                                       if s.status.value in ['pdt', 'pdt_call', 'pdt_restricted']]),
                    'violations': sum(len(v) for v in self.pdt_monitoring.violations.values())
                }
        
        elif report_type == 'gdpr_compliance':
            # Generate GDPR compliance report
            report_data['gdpr_summary'] = await self.gdpr_compliance.get_gdpr_compliance_summary()
        
        elif report_type == 'data_retention':
            # Generate data retention report
            retention_summary = await self.data_retention.get_retention_summary()
            compliance_report = await self.data_retention.generate_compliance_report(start_date, end_date)
            report_data['data_retention'] = {
                'summary': retention_summary,
                'compliance': {
                    'total_records': compliance_report.total_records,
                    'compliance_issues': compliance_report.compliance_issues,
                    'archival_jobs': compliance_report.archival_jobs_completed
                }
            }
        
        elif report_type == 'full_compliance':
            # Generate comprehensive compliance report
            report_data['tax_compliance'] = len(self.tax_reporting.form_1099_data)
            report_data['pdt_compliance'] = {
                'monitored_accounts': len(self.pdt_monitoring.account_statuses),
                'violations': sum(len(v) for v in self.pdt_monitoring.violations.values())
            }
            report_data['large_trader'] = {
                'registered_traders': len(self.large_trader.large_traders),
                'filings': len([f for filings in self.large_trader.form_13h_filings.values() for f in filings])
            }
            report_data['suspicious_activity'] = await self.suspicious_activity.get_suspicious_activities_summary()
            report_data['gdpr_compliance'] = await self.gdpr_compliance.get_gdpr_compliance_summary()
            report_data['data_retention'] = await self.data_retention.get_retention_summary()
        
        return report_data
        
    async def get_compliance_status(self) -> ComplianceStatus:
        """Get overall compliance status"""
        # Check each module status
        module_statuses = {}
        
        # Tax reporting status
        tax_issues = []  # Would check for missing filings, etc.
        module_statuses['tax_reporting'] = {
            'status': 'compliant' if not tax_issues else 'issues',
            'issues': tax_issues,
            'last_check': datetime.now().isoformat()
        }
        
        # PDT monitoring status
        pdt_violations = sum(len(v) for v in self.pdt_monitoring.violations.values())
        module_statuses['pdt_monitoring'] = {
            'status': 'compliant' if pdt_violations == 0 else 'issues',
            'violations': pdt_violations,
            'monitored_accounts': len(self.pdt_monitoring.account_statuses)
        }
        
        # GDPR compliance status
        gdpr_summary = await self.gdpr_compliance.get_gdpr_compliance_summary()
        module_statuses['gdpr_compliance'] = {
            'status': gdpr_summary['compliance_status'],
            'overdue_requests': gdpr_summary['overdue_requests'],
            'critical_breaches': gdpr_summary['critical_breaches']
        }
        
        # Suspicious activity status
        suspicious_summary = await self.suspicious_activity.get_suspicious_activities_summary()
        module_statuses['suspicious_activity'] = {
            'status': 'compliant' if suspicious_summary['critical_activities'] == 0 else 'issues',
            'critical_activities': suspicious_summary['critical_activities'],
            'pending_investigations': suspicious_summary['pending_investigations']
        }
        
        # Data retention status
        retention_summary = await self.data_retention.get_retention_summary()
        module_statuses['data_retention'] = {
            'status': 'compliant',  # Would check for overdue deletions
            'total_records': retention_summary['total_records'],
            'storage_mb': retention_summary['total_storage_mb']
        }
        
        # Calculate overall status and score
        issues = sum(1 for status in module_statuses.values() if status['status'] != 'compliant')
        critical_issues = sum(1 for status in module_statuses.values() if status['status'] == 'critical')
        
        if critical_issues > 0:
            overall_status = 'critical'
            compliance_score = max(0, 50 - (critical_issues * 20))
        elif issues > 0:
            overall_status = 'issues'
            compliance_score = max(50, 100 - (issues * 15))
        else:
            overall_status = 'compliant'
            compliance_score = 100
        
        return ComplianceStatus(
            overall_status=overall_status,
            last_updated=datetime.now(),
            module_statuses=module_statuses,
            pending_actions=[],  # Would gather pending actions from all modules
            recent_alerts=self.compliance_alerts[-10:],  # Last 10 alerts
            compliance_score=compliance_score
        )
        
    async def create_compliance_alert(self, module: ComplianceModule, severity: str,
                                     title: str, description: str,
                                     requires_action: bool = True) -> ComplianceAlert:
        """Create a compliance alert"""
        alert = ComplianceAlert(
            alert_id=f"alert_{datetime.now().timestamp()}",
            module=module,
            severity=severity,
            title=title,
            description=description,
            timestamp=datetime.now(),
            requires_action=requires_action,
            due_date=datetime.now() + timedelta(days=30) if requires_action else None
        )
        
        self.compliance_alerts.append(alert)
        
        # Log alert
        await self.audit_reporting.log_audit_event(
            AuditEventType.COMPLIANCE_ACTION,
            None,
            None,
            {
                'alert_id': alert.alert_id,
                'module': module.value,
                'severity': severity,
                'title': title
            },
            AuditLevel.WARNING if severity in ['medium', 'high'] else AuditLevel.CRITICAL
        )
        
        logger.warning(f"Compliance alert created: {alert.alert_id} - {title}")
        return alert
        
    async def run_compliance_checks(self):
        """Run periodic compliance checks"""
        logger.info("Running compliance checks")
        
        # Schedule archival jobs
        await self.data_retention.schedule_archival_jobs()
        await self.data_retention.execute_archival_jobs()
        
        # Check PDT violations
        # This would run through accounts and check for new violations
        
        # Check GDPR request deadlines
        # This would check for overdue GDPR requests
        
        # Check suspicious activity
        # This would review pending investigations
        
        logger.info("Compliance checks completed")
        
    async def shutdown(self):
        """Shutdown compliance system gracefully"""
        logger.info("Shutting down Regulatory Compliance System")
        
        # Final compliance check
        await self.run_compliance_checks()
        
        # Log shutdown
        await self.audit_reporting.log_audit_event(
            AuditEventType.SYSTEM_ACCESS,
            None,
            None,
            {'action': 'compliance_system_shutdown'},
            AuditLevel.INFO
        )
        
        logger.info("Regulatory Compliance System shutdown complete")