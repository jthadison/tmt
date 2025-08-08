"""Performance data export functionality."""

import csv
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any
from uuid import UUID
from io import StringIO

from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import TradePerformance, PerformanceMetrics, ExportRequest, TradeStatus
from .report_generator import PerformanceReportGenerator

logger = logging.getLogger(__name__)


class PerformanceExportManager:
    """Manages export functionality for performance data."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.report_generator = PerformanceReportGenerator(db_session)
    
    async def export_performance_data(self, request: ExportRequest) -> Dict[str, Any]:
        """Export performance data based on request parameters."""
        try:
            if request.export_format == 'csv':
                return await self._export_csv(request)
            elif request.export_format == 'json':
                return await self._export_json(request)
            elif request.export_format == 'pdf':
                return await self._export_pdf(request)
            elif request.export_format == 'xlsx':
                return await self._export_excel(request)
            else:
                raise ValueError(f"Unsupported export format: {request.export_format}")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
    
    async def _export_csv(self, request: ExportRequest) -> Dict[str, Any]:
        """Export data as CSV format."""
        if request.report_type == 'trades':
            return await self._export_trades_csv(request)
        elif request.report_type == 'tax':
            return await self._export_tax_csv(request)
        elif request.report_type == 'prop_firm':
            return await self._export_prop_firm_csv(request)
        else:
            return await self._export_metrics_csv(request)
    
    async def _export_trades_csv(self, request: ExportRequest) -> Dict[str, Any]:
        """Export trades data as CSV."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Trade ID', 'Account ID', 'Symbol', 'Entry Time', 'Exit Time',
            'Entry Price', 'Exit Price', 'Position Size', 'P&L', 'P&L %',
            'Commission', 'Swap', 'Duration (seconds)', 'Status'
        ])
        
        # Export trades for each account
        for account_id in request.account_ids:
            trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= request.start_date,
                    TradePerformance.entry_time <= request.end_date
                )
            ).order_by(TradePerformance.entry_time).all()
            
            for trade in trades:
                writer.writerow([
                    str(trade.trade_id),
                    str(trade.account_id),
                    trade.symbol,
                    trade.entry_time.isoformat() if trade.entry_time else '',
                    trade.exit_time.isoformat() if trade.exit_time else '',
                    float(trade.entry_price),
                    float(trade.exit_price) if trade.exit_price else '',
                    float(trade.position_size),
                    float(trade.pnl) if trade.pnl else '',
                    float(trade.pnl_percentage) if trade.pnl_percentage else '',
                    float(trade.commission) if trade.commission else 0,
                    float(trade.swap) if trade.swap else 0,
                    trade.trade_duration_seconds or '',
                    trade.status
                ])
        
        return {
            'content': output.getvalue(),
            'filename': f'trades_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'content_type': 'text/csv'
        }
    
    async def _export_tax_csv(self, request: ExportRequest) -> Dict[str, Any]:
        """Export data in tax reporting format (Form 8949)."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Form 8949 headers
        writer.writerow([
            'Description', 'Date Acquired', 'Date Sold', 
            'Proceeds', 'Cost Basis', 'Gain/Loss', 'Code'
        ])
        
        for account_id in request.account_ids:
            closed_trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.status == TradeStatus.CLOSED.value,
                    TradePerformance.entry_time >= request.start_date,
                    TradePerformance.exit_time <= request.end_date,
                    TradePerformance.pnl.isnot(None)
                )
            ).all()
            
            for trade in closed_trades:
                # Calculate proceeds and cost basis
                position_value = abs(float(trade.position_size * trade.exit_price))
                cost_basis = abs(float(trade.position_size * trade.entry_price))
                
                writer.writerow([
                    f"{trade.symbol} {abs(float(trade.position_size))} units",
                    trade.entry_time.strftime('%m/%d/%Y'),
                    trade.exit_time.strftime('%m/%d/%Y'),
                    f"{position_value:.2f}",
                    f"{cost_basis:.2f}",
                    f"{float(trade.pnl):.2f}",
                    'D'  # Code for derivative
                ])
        
        return {
            'content': output.getvalue(),
            'filename': f'tax_report_8949_{datetime.now().strftime("%Y%m%d")}.csv',
            'content_type': 'text/csv'
        }
    
    async def _export_json(self, request: ExportRequest) -> Dict[str, Any]:
        """Export data as JSON format."""
        data = {
            'export_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'account_ids': [str(aid) for aid in request.account_ids],
                'period_start': request.start_date.isoformat(),
                'period_end': request.end_date.isoformat(),
                'report_type': request.report_type
            },
            'accounts': []
        }
        
        for account_id in request.account_ids:
            # Get account performance data
            account_data = await self._collect_account_data(
                account_id, request.start_date, request.end_date, request.include_details
            )
            data['accounts'].append(account_data)
        
        return {
            'content': json.dumps(data, indent=2, default=str),
            'filename': f'performance_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            'content_type': 'application/json'
        }
    
    async def _collect_account_data(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime,
        include_details: bool
    ) -> Dict[str, Any]:
        """Collect comprehensive account data for export."""
        # Get monthly report for the period
        monthly_report = await self.report_generator.generate_custom_period_report(
            account_id, start_date, end_date, "Export Period"
        )
        
        account_data = {
            'account_id': str(account_id),
            'summary': monthly_report.get('summary', {}),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            }
        }
        
        if include_details:
            # Add detailed trade data
            trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= start_date,
                    TradePerformance.entry_time <= end_date
                )
            ).all()
            
            account_data['trades'] = [
                {
                    'trade_id': str(t.trade_id),
                    'symbol': t.symbol,
                    'entry_time': t.entry_time.isoformat(),
                    'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                    'pnl': float(t.pnl) if t.pnl else None,
                    'status': t.status
                }
                for t in trades
            ]
        
        return account_data
    
    async def _export_pdf(self, request: ExportRequest) -> Dict[str, Any]:
        """Export as PDF report (simplified implementation)."""
        # This would integrate with a PDF generation library like ReportLab
        # For now, return a placeholder
        return {
            'content': 'PDF generation not implemented',
            'filename': f'performance_report_{datetime.now().strftime("%Y%m%d")}.pdf',
            'content_type': 'application/pdf'
        }
    
    async def _export_excel(self, request: ExportRequest) -> Dict[str, Any]:
        """Export as Excel format (simplified implementation)."""
        # This would use libraries like openpyxl or xlsxwriter
        # For now, return a placeholder
        return {
            'content': 'Excel generation not implemented',
            'filename': f'performance_data_{datetime.now().strftime("%Y%m%d")}.xlsx',
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }