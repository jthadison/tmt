"""
Transaction History & Audit Trail System
Story 8.8 - Main integration module
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

try:
    from .transaction_manager import OandaTransactionManager, TransactionRecord, TransactionType
    from .transaction_filter import TransactionFilter, FilterCriteria
    from .transaction_exporter import TransactionExporter
    from .pl_analytics import PLAnalyticsEngine, DailyPLSummary, WeeklyPLSummary, MonthlyPLSummary
    from .audit_trail import AuditTrailManager, AuditRecord, AuditEventType
    from .data_retention import DataRetentionManager
    from .oanda_auth_handler import OandaAuthHandler
    from .connection_pool import OandaConnectionPool
except ImportError:
    from transaction_manager import OandaTransactionManager, TransactionRecord, TransactionType
    from transaction_filter import TransactionFilter, FilterCriteria
    from transaction_exporter import TransactionExporter
    from pl_analytics import PLAnalyticsEngine, DailyPLSummary, WeeklyPLSummary, MonthlyPLSummary
    from audit_trail import AuditTrailManager, AuditRecord, AuditEventType
    from data_retention import DataRetentionManager
    from oanda_auth_handler import OandaAuthHandler
    from connection_pool import OandaConnectionPool

logger = logging.getLogger(__name__)


class TransactionAuditSystem:
    """
    Comprehensive transaction history and audit trail system
    Integrates all components for Story 8.8
    """
    
    def __init__(self, 
                 auth_handler: OandaAuthHandler,
                 connection_pool: OandaConnectionPool,
                 storage_path: str = "./transaction_data"):
        """
        Initialize the transaction audit system
        
        Args:
            auth_handler: OANDA authentication handler
            connection_pool: Broker connection pool
            storage_path: Base path for data storage
        """
        self.auth_handler = auth_handler
        self.connection_pool = connection_pool
        
        # Initialize core components
        self.transaction_manager = OandaTransactionManager(auth_handler, connection_pool)
        self.transaction_filter = TransactionFilter()
        self.transaction_exporter = TransactionExporter()
        self.pl_analytics = PLAnalyticsEngine(self.transaction_manager)
        self.audit_trail = AuditTrailManager(self.transaction_manager)
        self.data_retention = DataRetentionManager(storage_path)
        
        # System state
        self.is_initialized = False
        self.last_sync_time: Optional[datetime] = None
        
    async def initialize(self):
        """Initialize the system"""
        if self.is_initialized:
            return
            
        logger.info("Initializing Transaction Audit System")
        
        # Initialize components
        await self._verify_connections()
        
        self.is_initialized = True
        logger.info("Transaction Audit System initialized successfully")
        
    # Transaction Management
    async def get_transaction_history(self,
                                    account_id: str,
                                    start_date: datetime,
                                    end_date: datetime,
                                    filters: Optional[FilterCriteria] = None) -> Dict[str, Any]:
        """
        Get filtered transaction history for an account
        
        Args:
            account_id: OANDA account ID
            start_date: Start of date range
            end_date: End of date range
            filters: Optional filter criteria
            
        Returns:
            Filtered transaction data with metadata
        """
        if not self.is_initialized:
            await self.initialize()
            
        # Get raw transactions
        result = await self.transaction_manager.get_transaction_history(
            account_id, start_date, end_date
        )
        
        transactions = result['transactions']
        
        # Apply filters if provided
        if filters:
            transactions = self.transaction_filter.filter_transactions(transactions, filters)
            
        return {
            'account_id': account_id,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'transaction_count': len(transactions),
            'transactions': transactions,
            'filters_applied': filters.to_dict() if filters else None,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    async def export_transactions(self,
                                account_id: str,
                                start_date: datetime,
                                end_date: datetime,
                                export_format: str = 'csv',
                                template: str = 'standard',
                                output_path: Optional[str] = None,
                                filters: Optional[FilterCriteria] = None) -> str:
        """
        Export transactions to various formats
        
        Args:
            account_id: OANDA account ID
            start_date: Start of date range
            end_date: End of date range
            export_format: Format (csv, excel, pdf, json)
            template: Export template (standard, tax, detailed, summary)
            output_path: Optional output file path
            filters: Optional filter criteria
            
        Returns:
            Path to exported file or content string
        """
        # Get transactions
        result = await self.get_transaction_history(account_id, start_date, end_date, filters)
        transactions = result['transactions']
        
        # Export based on format
        if export_format.lower() == 'csv':
            return await self.transaction_exporter.export_to_csv(
                transactions, output_path, template
            )
        elif export_format.lower() == 'excel':
            if not output_path:
                output_path = f"transactions_{account_id}_{start_date.date()}_to_{end_date.date()}.xlsx"
            return await self.transaction_exporter.export_to_excel(
                transactions, output_path, template
            )
        elif export_format.lower() == 'pdf':
            if not output_path:
                output_path = f"transactions_{account_id}_{start_date.date()}_to_{end_date.date()}.pdf"
            return await self.transaction_exporter.export_to_pdf(
                transactions, output_path, template
            )
        elif export_format.lower() == 'json':
            return await self.transaction_exporter.export_to_json(
                transactions, output_path
            )
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
            
    # P&L Analytics
    async def calculate_performance_metrics(self,
                                          account_id: str,
                                          start_date: datetime,
                                          end_date: datetime) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            account_id: OANDA account ID
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Performance metrics and analytics
        """
        # Get transactions
        result = await self.get_transaction_history(account_id, start_date, end_date)
        transactions = result['transactions']
        
        # Calculate daily P&L summaries
        daily_summaries = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            daily_summary = await self.pl_analytics.calculate_daily_pl(transactions, current_date)
            daily_summaries.append(daily_summary)
            current_date += timedelta(days=1)
            
        # Calculate monthly summary if period spans full month
        monthly_summaries = []
        if (end_date - start_date).days >= 28:
            month = start_date.month
            year = start_date.year
            monthly_summary = await self.pl_analytics.calculate_monthly_pl(transactions, year, month)
            monthly_summaries.append(monthly_summary)
            
        # Analyze performance trends
        trend_analysis = self.pl_analytics.analyze_performance_trend(transactions)
        
        return {
            'account_id': account_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'daily_summaries': [d.to_dict() for d in daily_summaries],
            'monthly_summaries': [m.to_dict() for m in monthly_summaries],
            'trend_analysis': trend_analysis.to_dict(),
            'calculated_at': datetime.utcnow().isoformat()
        }
        
    # Audit Trail Management
    async def record_signal_execution(self,
                                    signal_id: str,
                                    account_id: str,
                                    signal_data: Dict[str, Any],
                                    risk_score: float,
                                    compliance_status: str,
                                    correlation_id: Optional[str] = None) -> str:
        """
        Record complete signal execution audit trail
        
        Args:
            signal_id: Unique signal identifier
            account_id: Account ID
            signal_data: Signal parameters
            risk_score: Risk assessment score
            compliance_status: Compliance check result
            correlation_id: Optional correlation ID
            
        Returns:
            Audit record ID
        """
        # Record signal generation
        signal_audit_id = await self.audit_trail.record_signal_generated(
            signal_id, account_id, signal_data, correlation_id
        )
        
        # Record risk check
        risk_audit_id = await self.audit_trail.record_risk_check(
            signal_id, account_id, {'risk_score': risk_score}, 
            risk_score, risk_score < 80, correlation_id
        )
        
        # Record compliance check
        compliance_audit_id = await self.audit_trail.record_compliance_check(
            signal_id, account_id, {'status': compliance_status}, 
            compliance_status, correlation_id
        )
        
        logger.info(f"Recorded signal execution audit trail for {signal_id}")
        return signal_audit_id
        
    async def link_signal_to_transaction(self,
                                       signal_id: str,
                                       transaction_id: str,
                                       account_id: str,
                                       execution_latency_ms: Optional[float] = None) -> str:
        """
        Link trading signal to resulting transaction
        
        Args:
            signal_id: Original signal ID
            transaction_id: OANDA transaction ID
            account_id: Account ID
            execution_latency_ms: Execution latency
            
        Returns:
            Audit record ID
        """
        return await self.audit_trail.link_signal_to_transaction(
            signal_id, transaction_id, account_id, execution_latency_ms
        )
        
    async def generate_audit_report(self,
                                  start_date: datetime,
                                  end_date: datetime,
                                  account_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive audit report
        
        Args:
            start_date: Report period start
            end_date: Report period end
            account_ids: Optional list of account IDs
            
        Returns:
            Audit report data
        """
        report = await self.audit_trail.generate_audit_report(
            start_date, end_date, account_ids
        )
        return report.to_dict()
        
    # Data Retention Management
    async def archive_old_data(self, cutoff_months: int = 12) -> Dict[str, Any]:
        """
        Archive old transaction and audit data
        
        Args:
            cutoff_months: Archive data older than this many months
            
        Returns:
            Archive operation results
        """
        cutoff_date = date.today() - timedelta(days=cutoff_months * 30)
        
        # For demonstration, we'll create sample data to archive
        # In real implementation, this would get actual transaction/audit data
        
        results = {
            'operation_date': datetime.now().isoformat(),
            'cutoff_date': cutoff_date.isoformat(),
            'archives_created': [],
            'retention_reports': []
        }
        
        # Run retention maintenance
        reports = await self.data_retention.run_retention_maintenance()
        results['retention_reports'] = [r.to_dict() for r in reports]
        
        logger.info(f"Archived data older than {cutoff_date}")
        return results
        
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            'transaction_manager': {
                'cache_size': len(self.transaction_manager.transaction_cache),
                'last_cache_update': max(self.transaction_manager.last_cache_update.values()).isoformat() 
                    if self.transaction_manager.last_cache_update else None
            },
            'audit_trail': self.audit_trail.get_audit_statistics(),
            'data_retention': await self.data_retention.get_retention_statistics(),
            'system_status': {
                'initialized': self.is_initialized,
                'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None
            }
        }
        
    # Comprehensive reporting
    async def generate_compliance_report(self,
                                       account_id: str,
                                       start_date: datetime,
                                       end_date: datetime) -> Dict[str, Any]:
        """
        Generate compliance-focused report combining transactions and audit data
        
        Args:
            account_id: Account to report on
            start_date: Report period start
            end_date: Report period end
            
        Returns:
            Comprehensive compliance report
        """
        # Get transaction data
        transaction_data = await self.get_transaction_history(
            account_id, start_date, end_date
        )
        
        # Get performance metrics
        performance_data = await self.calculate_performance_metrics(
            account_id, start_date, end_date
        )
        
        # Get audit report
        audit_data = await self.generate_audit_report(
            start_date, end_date, [account_id]
        )
        
        # Combine into compliance report
        return {
            'report_type': 'compliance',
            'account_id': account_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'transaction_summary': {
                'total_transactions': transaction_data['transaction_count'],
                'transaction_types': self._summarize_transaction_types(transaction_data['transactions'])
            },
            'performance_summary': {
                'daily_summaries_count': len(performance_data['daily_summaries']),
                'trend_direction': performance_data['trend_analysis']['trend_direction']
            },
            'audit_summary': {
                'audit_coverage': audit_data['audit_coverage'],
                'compliance_violations': len(audit_data['compliance_violations']),
                'risk_events': len(audit_data['risk_events'])
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
    def _summarize_transaction_types(self, transactions: List[TransactionRecord]) -> Dict[str, int]:
        """Summarize transaction types"""
        type_counts = {}
        for transaction in transactions:
            tx_type = transaction.transaction_type
            type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
        return type_counts
        
    async def _verify_connections(self):
        """Verify system connections and dependencies"""
        # Verify auth handler has active sessions
        if not self.auth_handler.active_sessions:
            logger.warning("No active OANDA sessions found")
            
        # Test connection pool
        async with self.connection_pool.get_session() as session:
            logger.info("Connection pool test successful")
            
        logger.info("System connections verified")


# Convenience functions for common operations
async def quick_transaction_export(account_id: str,
                                 auth_handler: OandaAuthHandler,
                                 connection_pool: OandaConnectionPool,
                                 days_back: int = 30,
                                 export_format: str = 'csv') -> str:
    """
    Quick export of recent transactions
    
    Args:
        account_id: OANDA account ID
        auth_handler: Authentication handler
        connection_pool: Connection pool
        days_back: Number of days to look back
        export_format: Export format
        
    Returns:
        Export file path or content
    """
    system = TransactionAuditSystem(auth_handler, connection_pool)
    await system.initialize()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    return await system.export_transactions(
        account_id, start_date, end_date, export_format
    )


async def quick_performance_analysis(account_id: str,
                                   auth_handler: OandaAuthHandler,
                                   connection_pool: OandaConnectionPool,
                                   days_back: int = 30) -> Dict[str, Any]:
    """
    Quick performance analysis for recent period
    
    Args:
        account_id: OANDA account ID
        auth_handler: Authentication handler
        connection_pool: Connection pool
        days_back: Number of days to analyze
        
    Returns:
        Performance analysis results
    """
    system = TransactionAuditSystem(auth_handler, connection_pool)
    await system.initialize()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    return await system.calculate_performance_metrics(
        account_id, start_date, end_date
    )