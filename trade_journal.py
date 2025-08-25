#!/usr/bin/env python3
"""
Simple Trade Journal CSV Export Service
Generates CSV exports of trading activity for analysis and record keeping
"""

import os
import csv
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class TradeJournal:
    """Simple trade journal for CSV export functionality"""
    
    def __init__(self):
        self.journal_file = "trade_journal.json"
        self.trades = self._load_trades()
        
    def _load_trades(self) -> List[Dict]:
        """Load trades from journal file"""
        if os.path.exists(self.journal_file):
            try:
                with open(self.journal_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading trade journal: {e}")
                return []
        return []
    
    def _save_trades(self):
        """Save trades to journal file"""
        try:
            with open(self.journal_file, 'w') as f:
                json.dump(self.trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trade journal: {e}")
    
    def record_trade(self, trade_data: Dict[str, Any]):
        """Record a trade in the journal"""
        try:
            # Extract key information
            trade_record = {
                "timestamp": datetime.now().isoformat(),
                "trade_id": trade_data.get("trade_id", ""),
                "instrument": trade_data.get("instrument", ""),
                "side": "BUY" if float(trade_data.get("units_filled", 0)) > 0 else "SELL",
                "units": abs(float(trade_data.get("units_filled", 0))),
                "entry_price": float(trade_data.get("fill_price", 0)),
                "stop_loss": trade_data.get("stop_loss_price"),
                "take_profit": trade_data.get("take_profit_price"),
                "mode": trade_data.get("mode", "unknown"),
                "success": trade_data.get("success", False),
                "pl": float(trade_data.get("pl", 0)),
                "commission": float(trade_data.get("commission", 0)),
                "financing": float(trade_data.get("financing", 0)),
                "signal_id": trade_data.get("signal_id"),
                "status": "OPEN"  # Will be updated when closed
            }
            
            self.trades.append(trade_record)
            self._save_trades()
            logger.info(f"Trade recorded: {trade_record['trade_id']} - {trade_record['instrument']}")
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def update_trade_close(self, trade_id: str, close_data: Dict[str, Any]):
        """Update trade with close information"""
        try:
            for trade in self.trades:
                if trade.get("trade_id") == trade_id:
                    trade.update({
                        "close_timestamp": datetime.now().isoformat(),
                        "close_price": close_data.get("close_price"),
                        "close_pl": close_data.get("close_pl"),
                        "close_reason": close_data.get("reason", "manual"),
                        "status": "CLOSED"
                    })
                    self._save_trades()
                    logger.info(f"Trade updated with close data: {trade_id}")
                    break
        except Exception as e:
            logger.error(f"Error updating trade close: {e}")
    
    def export_to_csv(self, filename: Optional[str] = None, days_back: Optional[int] = None) -> str:
        """Export trades to CSV format"""
        try:
            if filename is None:
                filename = f"trade_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Filter trades by date if specified
            trades_to_export = self.trades
            if days_back:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                trades_to_export = [
                    trade for trade in self.trades 
                    if datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) >= cutoff_date
                ]
            
            # Define CSV headers
            headers = [
                'Timestamp', 'Trade ID', 'Instrument', 'Side', 'Units', 'Entry Price',
                'Stop Loss', 'Take Profit', 'Mode', 'Success', 'P&L', 'Commission',
                'Financing', 'Signal ID', 'Status', 'Close Timestamp', 'Close Price',
                'Close P&L', 'Close Reason'
            ]
            
            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for trade in trades_to_export:
                    row = [
                        trade.get('timestamp', ''),
                        trade.get('trade_id', ''),
                        trade.get('instrument', ''),
                        trade.get('side', ''),
                        trade.get('units', ''),
                        trade.get('entry_price', ''),
                        trade.get('stop_loss', ''),
                        trade.get('take_profit', ''),
                        trade.get('mode', ''),
                        trade.get('success', ''),
                        trade.get('pl', ''),
                        trade.get('commission', ''),
                        trade.get('financing', ''),
                        trade.get('signal_id', ''),
                        trade.get('status', ''),
                        trade.get('close_timestamp', ''),
                        trade.get('close_price', ''),
                        trade.get('close_pl', ''),
                        trade.get('close_reason', '')
                    ]
                    writer.writerow(row)
            
            logger.info(f"CSV export completed: {filename} ({len(trades_to_export)} trades)")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise
    
    def get_summary(self) -> Dict[str, Any]:
        """Get trading summary statistics"""
        try:
            total_trades = len(self.trades)
            successful_trades = len([t for t in self.trades if t.get('success', False)])
            closed_trades = len([t for t in self.trades if t.get('status') == 'CLOSED'])
            open_trades = len([t for t in self.trades if t.get('status') == 'OPEN'])
            
            total_pl = sum(float(t.get('pl', 0)) for t in self.trades)
            total_commission = sum(float(t.get('commission', 0)) for t in self.trades)
            
            # Calculate success rate
            success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "successful_trades": successful_trades,
                "closed_trades": closed_trades,
                "open_trades": open_trades,
                "success_rate_percent": round(success_rate, 2),
                "total_pl": round(total_pl, 2),
                "total_commission": round(total_commission, 2),
                "net_pl": round(total_pl - total_commission, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating summary: {e}")
            return {}

# Global instance
trade_journal = TradeJournal()

def record_trade_execution(trade_data: Dict[str, Any]):
    """Convenience function to record trade execution"""
    try:
        trade_journal.record_trade(trade_data)
    except Exception as e:
        logger.error(f"Error recording trade execution: {e}")

def record_trade_close(trade_id: str, close_data: Dict[str, Any]):
    """Convenience function to record trade close"""
    try:
        trade_journal.update_trade_close(trade_id, close_data)
    except Exception as e:
        logger.error(f"Error recording trade close: {e}")

def export_csv(filename: Optional[str] = None, days_back: Optional[int] = None) -> str:
    """Convenience function to export CSV"""
    return trade_journal.export_to_csv(filename, days_back)

def get_trading_summary() -> Dict[str, Any]:
    """Convenience function to get trading summary"""
    return trade_journal.get_summary()