"""
Transaction Filtering Module
Story 8.8 - Task 2: Implement transaction filtering
"""
import logging
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

try:
    from .transaction_manager import TransactionRecord, TransactionType
except ImportError:
    from transaction_manager import TransactionRecord, TransactionType

logger = logging.getLogger(__name__)


@dataclass
class FilterCriteria:
    """Criteria for filtering transactions"""
    transaction_types: Optional[List[TransactionType]] = None
    instruments: Optional[List[str]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    min_pl: Optional[Decimal] = None
    max_pl: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trade_ids: Optional[List[str]] = None
    order_ids: Optional[List[str]] = None
    exclude_zero_pl: bool = False
    exclude_financing: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = {}
        if self.transaction_types:
            result['transaction_types'] = [t.value for t in self.transaction_types]
        if self.instruments:
            result['instruments'] = self.instruments
        if self.min_amount is not None:
            result['min_amount'] = str(self.min_amount)
        if self.max_amount is not None:
            result['max_amount'] = str(self.max_amount)
        if self.min_pl is not None:
            result['min_pl'] = str(self.min_pl)
        if self.max_pl is not None:
            result['max_pl'] = str(self.max_pl)
        if self.start_date:
            result['start_date'] = self.start_date.isoformat()
        if self.end_date:
            result['end_date'] = self.end_date.isoformat()
        if self.trade_ids:
            result['trade_ids'] = self.trade_ids
        if self.order_ids:
            result['order_ids'] = self.order_ids
        result['exclude_zero_pl'] = self.exclude_zero_pl
        result['exclude_financing'] = self.exclude_financing
        return result


class TransactionFilter:
    """Provides advanced filtering capabilities for transactions"""
    
    def __init__(self):
        self.filter_cache: Dict[str, List[TransactionRecord]] = {}
        
    def filter_transactions(self, 
                          transactions: List[TransactionRecord], 
                          criteria: FilterCriteria) -> List[TransactionRecord]:
        """
        Filter transactions based on multiple criteria
        
        Args:
            transactions: List of transactions to filter
            criteria: FilterCriteria object with filter parameters
            
        Returns:
            Filtered list of transactions
        """
        filtered = transactions.copy()
        
        # Apply type filter
        if criteria.transaction_types:
            type_values = [t.value for t in criteria.transaction_types]
            filtered = [t for t in filtered if t.transaction_type in type_values]
            
        # Apply instrument filter
        if criteria.instruments:
            filtered = [t for t in filtered if t.instrument in criteria.instruments]
            
        # Apply amount range filter
        if criteria.min_amount is not None:
            filtered = [t for t in filtered if abs(t.units) >= criteria.min_amount]
        if criteria.max_amount is not None:
            filtered = [t for t in filtered if abs(t.units) <= criteria.max_amount]
            
        # Apply P&L range filter
        if criteria.min_pl is not None:
            filtered = [t for t in filtered if t.pl >= criteria.min_pl]
        if criteria.max_pl is not None:
            filtered = [t for t in filtered if t.pl <= criteria.max_pl]
            
        # Apply date range filter
        if criteria.start_date:
            filtered = [t for t in filtered if t.timestamp >= criteria.start_date]
        if criteria.end_date:
            filtered = [t for t in filtered if t.timestamp <= criteria.end_date]
            
        # Apply trade ID filter
        if criteria.trade_ids:
            filtered = [t for t in filtered if t.trade_id in criteria.trade_ids]
            
        # Apply order ID filter
        if criteria.order_ids:
            filtered = [t for t in filtered if t.order_id in criteria.order_ids]
            
        # Exclude zero P&L transactions
        if criteria.exclude_zero_pl:
            filtered = [t for t in filtered if t.pl != Decimal('0')]
            
        # Exclude financing transactions
        if criteria.exclude_financing:
            filtered = [t for t in filtered if t.transaction_type != 'DAILY_FINANCING']
            
        return filtered
        
    def filter_by_instrument(self, 
                            transactions: List[TransactionRecord], 
                            instrument: str) -> List[TransactionRecord]:
        """Filter transactions by specific instrument"""
        return [t for t in transactions if t.instrument == instrument]
        
    def filter_by_type(self, 
                      transactions: List[TransactionRecord], 
                      transaction_type: TransactionType) -> List[TransactionRecord]:
        """Filter transactions by specific type"""
        return [t for t in transactions if t.transaction_type == transaction_type.value]
        
    def filter_profitable_trades(self, 
                                transactions: List[TransactionRecord]) -> List[TransactionRecord]:
        """Filter only profitable transactions"""
        return [t for t in transactions if t.pl > Decimal('0')]
        
    def filter_losing_trades(self, 
                           transactions: List[TransactionRecord]) -> List[TransactionRecord]:
        """Filter only losing transactions"""
        return [t for t in transactions if t.pl < Decimal('0')]
        
    def filter_by_date_range(self, 
                            transactions: List[TransactionRecord],
                            start_date: datetime,
                            end_date: datetime) -> List[TransactionRecord]:
        """Filter transactions within date range"""
        return [t for t in transactions 
                if start_date <= t.timestamp <= end_date]
        
    def group_by_instrument(self, 
                          transactions: List[TransactionRecord]) -> Dict[str, List[TransactionRecord]]:
        """Group transactions by instrument"""
        grouped = {}
        for transaction in transactions:
            instrument = transaction.instrument or 'UNKNOWN'
            if instrument not in grouped:
                grouped[instrument] = []
            grouped[instrument].append(transaction)
        return grouped
        
    def group_by_type(self, 
                     transactions: List[TransactionRecord]) -> Dict[str, List[TransactionRecord]]:
        """Group transactions by type"""
        grouped = {}
        for transaction in transactions:
            tx_type = transaction.transaction_type
            if tx_type not in grouped:
                grouped[tx_type] = []
            grouped[tx_type].append(transaction)
        return grouped
        
    def group_by_day(self, 
                    transactions: List[TransactionRecord]) -> Dict[str, List[TransactionRecord]]:
        """Group transactions by day"""
        grouped = {}
        for transaction in transactions:
            day_key = transaction.timestamp.date().isoformat()
            if day_key not in grouped:
                grouped[day_key] = []
            grouped[day_key].append(transaction)
        return grouped
        
    def apply_custom_filter(self, 
                          transactions: List[TransactionRecord],
                          filter_func: Callable[[TransactionRecord], bool]) -> List[TransactionRecord]:
        """Apply a custom filter function"""
        return [t for t in transactions if filter_func(t)]
        
    def create_optimized_filter_chain(self, criteria: FilterCriteria) -> Callable:
        """
        Create an optimized filter chain for repeated use
        
        Args:
            criteria: FilterCriteria to optimize
            
        Returns:
            Optimized filter function
        """
        filters = []
        
        # Build filter chain
        if criteria.transaction_types:
            type_values = [t.value for t in criteria.transaction_types]
            filters.append(lambda t: t.transaction_type in type_values)
            
        if criteria.instruments:
            filters.append(lambda t: t.instrument in criteria.instruments)
            
        if criteria.min_amount is not None:
            filters.append(lambda t: abs(t.units) >= criteria.min_amount)
            
        if criteria.max_amount is not None:
            filters.append(lambda t: abs(t.units) <= criteria.max_amount)
            
        if criteria.min_pl is not None:
            filters.append(lambda t: t.pl >= criteria.min_pl)
            
        if criteria.max_pl is not None:
            filters.append(lambda t: t.pl <= criteria.max_pl)
            
        if criteria.exclude_zero_pl:
            filters.append(lambda t: t.pl != Decimal('0'))
            
        if criteria.exclude_financing:
            filters.append(lambda t: t.transaction_type != 'DAILY_FINANCING')
            
        # Create combined filter
        def combined_filter(transaction: TransactionRecord) -> bool:
            return all(f(transaction) for f in filters)
            
        return combined_filter