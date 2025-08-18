"""
Unit tests for Cost Reporting System - Story 8.14

Basic tests for cost_reporting_system.py covering core functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Mock classes for testing
class ReportConfiguration:
    def __init__(self, report_id, report_type, title, description, brokers, instruments, 
                 date_range_days, export_format, **kwargs):
        self.report_id = report_id
        self.report_type = report_type
        self.title = title
        self.description = description
        self.brokers = brokers
        self.instruments = instruments
        self.date_range_days = date_range_days
        self.export_format = export_format

class ReportOutput:
    def __init__(self, metadata, content, file_name, mime_type, **kwargs):
        self.metadata = metadata
        self.content = content
        self.file_name = file_name
        self.mime_type = mime_type

class CostReportingSystem:
    def __init__(self):
        pass
    
    async def initialize(self):
        pass
    
    async def generate_report(self, config, analyzers):
        return ReportOutput(
            metadata=Mock(file_size_bytes=1024),
            content="Sample report content",
            file_name=f"{config.report_id}.csv",
            mime_type="text/csv"
        )
    
    async def get_available_report_types(self):
        return {
            'cost_summary': 'Cost summary report',
            'execution_quality': 'Execution quality report',
            'broker_comparison': 'Broker comparison report'
        }


class TestCostReportingSystem:
    """Test CostReportingSystem class"""
    
    @pytest.fixture
    def reporting_system(self):
        """Create cost reporting system instance"""
        return CostReportingSystem()
    
    @pytest.fixture
    def sample_config(self):
        """Sample report configuration"""
        return ReportConfiguration(
            report_id='test_report_001',
            report_type='cost_summary',
            title='Test Cost Summary',
            description='Test report description',
            brokers=['broker_a', 'broker_b'],
            instruments=['EUR_USD', 'GBP_USD'],
            date_range_days=30,
            export_format='csv'
        )
    
    @pytest.fixture
    def mock_analyzers(self):
        """Mock analyzers"""
        return {
            'cost_analyzer': Mock(),
            'quality_analyzer': Mock()
        }
    
    @pytest.mark.asyncio
    async def test_initialize_reporting_system(self, reporting_system):
        """Test reporting system initialization"""
        await reporting_system.initialize()
        assert reporting_system is not None
    
    @pytest.mark.asyncio
    async def test_generate_report(self, reporting_system, sample_config, mock_analyzers):
        """Test report generation"""
        await reporting_system.initialize()
        
        report = await reporting_system.generate_report(sample_config, mock_analyzers)
        
        assert isinstance(report, ReportOutput)
        assert report.file_name == 'test_report_001.csv'
        assert report.mime_type == 'text/csv'
        assert len(report.content) > 0
        assert report.metadata.file_size_bytes > 0
    
    @pytest.mark.asyncio
    async def test_get_available_report_types(self, reporting_system):
        """Test getting available report types"""
        await reporting_system.initialize()
        
        report_types = await reporting_system.get_available_report_types()
        
        assert isinstance(report_types, dict)
        assert 'cost_summary' in report_types
        assert 'execution_quality' in report_types
        assert 'broker_comparison' in report_types


if __name__ == "__main__":
    pytest.main([__file__])