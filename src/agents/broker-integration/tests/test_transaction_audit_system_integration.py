"""
Integration Tests for Transaction Audit System
Story 8.8 - Complete system integration tests
"""
import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transaction_audit_system import TransactionAuditSystem, quick_transaction_export, quick_performance_analysis
from transaction_filter import FilterCriteria, TransactionType
from oanda_auth_handler import OandaAuthHandler, AccountContext, Environment


class TestTransactionAuditSystemIntegration:
    """Integration tests for the complete Transaction Audit System"""
    
    @pytest.fixture
    def temp_storage(self):
        """Temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def mock_auth_handler(self):
        """Mock authentication handler with active session"""
        auth_handler = MagicMock(spec=OandaAuthHandler)
        
        context = AccountContext(
            user_id="test_user",
            account_id="test_account_123",
            environment=Environment.PRACTICE,
            api_key="test_api_key",
            base_url="https://api-fxpractice.oanda.com",
            authenticated_at=datetime.now(timezone.utc),
            last_refresh=datetime.now(timezone.utc)
        )
        
        auth_handler.active_sessions = {"test_account_123": context}
        return auth_handler
        
    @pytest.fixture
    def mock_connection_pool(self):
        """Mock connection pool with sample transaction data"""
        pool = MagicMock()
        
        # Mock transaction response
        sample_transactions = {
            'transactions': [
                {
                    'id': '1',
                    'type': 'ORDER_FILL',
                    'instrument': 'EUR_USD',
                    'units': '1000',
                    'price': '1.1000',
                    'pl': '25.50',
                    'commission': '1.00',
                    'financing': '0.00',
                    'time': '2024-01-15T10:00:00.000000Z',
                    'accountBalance': '1025.50',
                    'reason': 'MARKET_ORDER',
                    'tradeID': 'T1'
                },
                {
                    'id': '2',
                    'type': 'TRADE_CLOSE',
                    'instrument': 'GBP_USD',
                    'units': '-500',
                    'price': '1.2500',
                    'pl': '-15.25',
                    'commission': '0.50',
                    'financing': '0.25',
                    'time': '2024-01-15T14:30:00.000000Z',
                    'accountBalance': '1009.50',
                    'reason': 'STOP_LOSS',
                    'tradeID': 'T2'
                },
                {
                    'id': '3',
                    'type': 'ORDER_FILL',
                    'instrument': 'USD_JPY',
                    'units': '2000',
                    'price': '110.50',
                    'pl': '30.75',
                    'commission': '1.50',
                    'financing': '0.00',
                    'time': '2024-01-16T09:15:00.000000Z',
                    'accountBalance': '1038.75',
                    'reason': 'MARKET_ORDER',
                    'tradeID': 'T3'
                },
                {
                    'id': '4',
                    'type': 'DAILY_FINANCING',
                    'instrument': None,
                    'units': '0',
                    'price': '0.00',
                    'pl': '0.00',
                    'commission': '0.00',
                    'financing': '-2.50',
                    'time': '2024-01-16T21:00:00.000000Z',
                    'accountBalance': '1036.25',
                    'reason': 'DAILY_FINANCING'
                }
            ],
            'lastTransactionID': '4',
            'pages': []
        }
        
        session = MagicMock()
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value=sample_transactions)
        
        # Create properly configured async context manager for response
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=response)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        session.get = AsyncMock(return_value=async_context_manager)
        
        # Mock the session context manager
        session_context = AsyncMock()
        session_context.__aenter__ = AsyncMock(return_value=session)
        session_context.__aexit__ = AsyncMock(return_value=None)
        pool.get_session = MagicMock(return_value=session_context)
        
        return pool
        
    @pytest_asyncio.fixture
    async def audit_system(self, mock_auth_handler, mock_connection_pool, temp_storage):
        """Initialized audit system"""
        system = TransactionAuditSystem(
            mock_auth_handler, 
            mock_connection_pool,
            temp_storage
        )
        await system.initialize()
        return system
        
    @pytest.mark.asyncio
    async def test_complete_transaction_workflow(self, audit_system):
        """Test complete workflow from fetching to analysis"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # 1. Get transaction history
        transaction_data = await audit_system.get_transaction_history(
            account_id, start_date, end_date
        )
        
        assert transaction_data['account_id'] == account_id
        assert transaction_data['transaction_count'] == 4
        assert len(transaction_data['transactions']) == 4
        
        # 2. Calculate performance metrics
        performance_data = await audit_system.calculate_performance_metrics(
            account_id, start_date, end_date
        )
        
        assert 'daily_summaries' in performance_data
        assert 'trend_analysis' in performance_data
        assert len(performance_data['daily_summaries']) > 0
        
        # 3. Generate audit report
        audit_report = await audit_system.generate_audit_report(
            start_date, end_date, [account_id]
        )
        
        assert 'total_signals' in audit_report
        assert 'audit_coverage' in audit_report
        
    @pytest.mark.asyncio
    async def test_transaction_filtering(self, audit_system):
        """Test transaction filtering functionality"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Filter for only profitable trades
        filters = FilterCriteria(
            transaction_types=[TransactionType.ORDER_FILL, TransactionType.TRADE_CLOSE],
            min_pl=Decimal('0')
        )
        
        filtered_data = await audit_system.get_transaction_history(
            account_id, start_date, end_date, filters
        )
        
        # Should only include profitable trades
        profitable_trades = [
            t for t in filtered_data['transactions'] 
            if t.pl > 0
        ]
        assert len(profitable_trades) == len(filtered_data['transactions'])
        
    @pytest.mark.asyncio
    async def test_export_functionality(self, audit_system, temp_storage):
        """Test various export formats"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Test CSV export
        csv_path = await audit_system.export_transactions(
            account_id, start_date, end_date, 
            export_format='csv',
            output_path=os.path.join(temp_storage, 'test.csv')
        )
        
        assert os.path.exists(csv_path)
        
        # Test JSON export
        json_content = await audit_system.export_transactions(
            account_id, start_date, end_date,
            export_format='json'
        )
        
        assert 'export_date' in json_content
        assert 'transactions' in json_content
        
        # Test Excel export (if available)
        try:
            excel_path = await audit_system.export_transactions(
                account_id, start_date, end_date,
                export_format='excel',
                output_path=os.path.join(temp_storage, 'test.xlsx')
            )
            assert os.path.exists(excel_path)
        except ImportError:
            # Excel export requires openpyxl
            pass
            
    @pytest.mark.asyncio
    async def test_signal_audit_trail(self, audit_system):
        """Test complete signal audit trail"""
        signal_id = "test_signal_123"
        account_id = "test_account_123"
        
        # Record signal execution
        signal_data = {
            "instrument": "EUR_USD",
            "direction": "long",
            "confidence": 0.85,
            "entry_price": 1.1000
        }
        
        audit_id = await audit_system.record_signal_execution(
            signal_id, account_id, signal_data, 
            risk_score=65.0, 
            compliance_status="PASSED"
        )
        
        assert audit_id is not None
        
        # Link to transaction
        transaction_id = "txn_test_123"
        link_id = await audit_system.link_signal_to_transaction(
            signal_id, transaction_id, account_id, execution_latency_ms=125.5
        )
        
        assert link_id is not None
        
        # Verify trail exists
        trail = await audit_system.audit_trail.get_signal_execution_trail(signal_id)
        assert trail is not None
        assert trail.execution_success is True
        assert trail.execution_latency_ms == 125.5
        assert transaction_id in trail.transaction_ids
        
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, audit_system):
        """Test comprehensive compliance report"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        compliance_report = await audit_system.generate_compliance_report(
            account_id, start_date, end_date
        )
        
        assert compliance_report['report_type'] == 'compliance'
        assert compliance_report['account_id'] == account_id
        assert 'transaction_summary' in compliance_report
        assert 'performance_summary' in compliance_report
        assert 'audit_summary' in compliance_report
        assert 'generated_at' in compliance_report
        
        # Check transaction summary
        tx_summary = compliance_report['transaction_summary']
        assert 'total_transactions' in tx_summary
        assert 'transaction_types' in tx_summary
        assert tx_summary['total_transactions'] == 4
        
    @pytest.mark.asyncio
    async def test_data_archiving_workflow(self, audit_system):
        """Test data archiving and retention"""
        # Archive old data (simplified test)
        archive_results = await audit_system.archive_old_data(cutoff_months=6)
        
        assert 'operation_date' in archive_results
        assert 'cutoff_date' in archive_results
        assert 'retention_reports' in archive_results
        
    @pytest.mark.asyncio
    async def test_system_statistics(self, audit_system):
        """Test system statistics collection"""
        stats = await audit_system.get_system_statistics()
        
        assert 'transaction_manager' in stats
        assert 'audit_trail' in stats
        assert 'data_retention' in stats
        assert 'system_status' in stats
        
        # Check system status
        system_status = stats['system_status']
        assert system_status['initialized'] is True
        
    @pytest.mark.asyncio
    async def test_performance_analytics_integration(self, audit_system):
        """Test performance analytics integration"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 16)
        
        performance_data = await audit_system.calculate_performance_metrics(
            account_id, start_date, end_date
        )
        
        # Check daily summaries
        daily_summaries = performance_data['daily_summaries']
        assert len(daily_summaries) == 2  # 2 days
        
        # Check that we have data for the trading days
        trading_days = [d for d in daily_summaries if d['trade_count'] > 0]
        assert len(trading_days) >= 1
        
        # Check trend analysis
        trend_analysis = performance_data['trend_analysis']
        assert 'trend_direction' in trend_analysis
        assert 'consistency_score' in trend_analysis
        
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, audit_system, mock_connection_pool):
        """Test error handling across the system"""
        # Mock API error
        session = MagicMock()
        response = MagicMock()
        response.status = 500
        response.text = AsyncMock(return_value="Internal Server Error")
        
        session.get = AsyncMock(return_value=response)
        mock_connection_pool.get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Should handle API errors gracefully
        with pytest.raises(Exception):
            await audit_system.get_transaction_history(
                account_id, start_date, end_date
            )
            
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, audit_system):
        """Test concurrent operations on the system"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Run multiple operations concurrently
        tasks = [
            audit_system.get_transaction_history(account_id, start_date, end_date),
            audit_system.calculate_performance_metrics(account_id, start_date, end_date),
            audit_system.generate_audit_report(start_date, end_date, [account_id])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete without errors
        for result in results:
            assert not isinstance(result, Exception)
            
    @pytest.mark.asyncio
    async def test_quick_convenience_functions(self, mock_auth_handler, mock_connection_pool):
        """Test convenience functions"""
        account_id = "test_account_123"
        
        # Test quick export
        export_result = await quick_transaction_export(
            account_id, mock_auth_handler, mock_connection_pool,
            days_back=7, export_format='csv'
        )
        
        assert isinstance(export_result, str)
        
        # Test quick analysis
        analysis_result = await quick_performance_analysis(
            account_id, mock_auth_handler, mock_connection_pool,
            days_back=7
        )
        
        assert 'daily_summaries' in analysis_result
        assert 'trend_analysis' in analysis_result
        
    @pytest.mark.asyncio
    async def test_multi_instrument_analysis(self, audit_system):
        """Test analysis across multiple instruments"""
        account_id = "test_account_123"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Get transactions and group by instrument
        transaction_data = await audit_system.get_transaction_history(
            account_id, start_date, end_date
        )
        
        transactions = transaction_data['transactions']
        
        # Group by instrument using the filter
        eur_usd_filter = FilterCriteria(instruments=['EUR_USD'])
        eur_usd_data = audit_system.transaction_filter.filter_transactions(
            transactions, eur_usd_filter
        )
        
        gbp_usd_filter = FilterCriteria(instruments=['GBP_USD'])
        gbp_usd_data = audit_system.transaction_filter.filter_transactions(
            transactions, gbp_usd_filter
        )
        
        # Should have transactions for both instruments
        assert len(eur_usd_data) > 0
        assert len(gbp_usd_data) > 0
        
        # All EUR_USD transactions should be EUR_USD
        assert all(t.instrument == 'EUR_USD' for t in eur_usd_data)
        assert all(t.instrument == 'GBP_USD' for t in gbp_usd_data)
        
    @pytest.mark.asyncio
    async def test_time_zone_handling(self, audit_system):
        """Test proper time zone handling"""
        account_id = "test_account_123"
        
        # Test with different time zones
        utc_start = datetime(2024, 1, 15, 0, 0, 0)
        utc_end = datetime(2024, 1, 15, 23, 59, 59)
        
        transaction_data = await audit_system.get_transaction_history(
            account_id, utc_start, utc_end
        )
        
        # Should handle UTC times correctly
        assert transaction_data['transaction_count'] >= 0
        
        # Check that timestamps are parsed correctly
        if transaction_data['transactions']:
            for transaction in transaction_data['transactions']:
                assert isinstance(transaction.timestamp, datetime)
                
    def test_serialization_integration(self, audit_system):
        """Test that all data structures serialize correctly"""
        # Test filter criteria serialization
        filters = FilterCriteria(
            transaction_types=[TransactionType.ORDER_FILL],
            min_pl=Decimal('10.0'),
            exclude_zero_pl=True
        )
        
        filter_dict = filters.to_dict()
        assert 'transaction_types' in filter_dict
        assert 'min_pl' in filter_dict
        assert filter_dict['exclude_zero_pl'] is True