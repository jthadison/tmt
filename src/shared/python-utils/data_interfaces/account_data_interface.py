"""
Account Data Interface

Abstract interface for account data providers, allowing seamless switching
between mock data and real account information from databases or brokers.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class AccountStatus(Enum):
    """Account status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    UNDER_REVIEW = "under_review"


@dataclass
class AccountInfo:
    """Account information"""
    account_id: str
    prop_firm: str
    account_type: str  # 'demo', 'live', 'challenge'
    balance: Decimal
    equity: Decimal
    margin_used: Decimal
    margin_free: Decimal
    status: AccountStatus
    max_daily_loss: Decimal
    max_total_loss: Decimal
    profit_target: Optional[Decimal] = None
    created_date: datetime = datetime.now()


@dataclass
class Position:
    """Open position information"""
    position_id: str
    account_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    timestamp: datetime


class AccountDataInterface(ABC):
    """Abstract interface for account data providers"""
    
    @abstractmethod
    async def get_account_info(self, account_id: str) -> Optional[AccountInfo]:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_all_accounts(self) -> List[AccountInfo]:
        """Get all managed accounts"""
        pass
    
    @abstractmethod
    async def get_open_positions(self, account_id: str) -> List[Position]:
        """Get open positions for an account"""
        pass
    
    @abstractmethod
    async def update_account_balance(self, account_id: str, new_balance: Decimal) -> bool:
        """Update account balance"""
        pass
    
    @abstractmethod
    async def get_accounts_by_prop_firm(self, prop_firm: str) -> List[AccountInfo]:
        """Get accounts filtered by prop firm"""
        pass


class MockAccountDataProvider(AccountDataInterface):
    """Mock implementation for development and testing"""
    
    def __init__(self):
        self._mock_accounts = self._generate_mock_accounts()
        self._mock_positions = self._generate_mock_positions()
    
    def _generate_mock_accounts(self) -> List[AccountInfo]:
        """Generate mock account data"""
        accounts = []
        prop_firms = ["FTMO", "MyForexFunds", "FundedNext", "TradingForum"]
        
        for i in range(10):
            account = AccountInfo(
                account_id=f"ACC{i:03d}",
                prop_firm=prop_firms[i % len(prop_firms)],
                account_type="live" if i % 3 == 0 else "demo",
                balance=Decimal('10000') + Decimal(str(i * 1000)),
                equity=Decimal('10000') + Decimal(str(i * 1000)) + Decimal(str((i % 5) * 100)),
                margin_used=Decimal(str(i * 100)),
                margin_free=Decimal('9000') + Decimal(str(i * 900)),
                status=AccountStatus.ACTIVE if i % 4 != 3 else AccountStatus.INACTIVE,
                max_daily_loss=Decimal('500'),
                max_total_loss=Decimal('1000'),
                profit_target=Decimal('1000') if i % 2 == 0 else None,
                created_date=datetime.now()
            )
            accounts.append(account)
        
        return accounts
    
    def _generate_mock_positions(self) -> List[Position]:
        """Generate mock position data"""
        positions = []
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
        
        for i in range(5):
            account_id = f"ACC{i:03d}"
            symbol = symbols[i % len(symbols)]
            side = "buy" if i % 2 == 0 else "sell"
            
            entry_price = Decimal('1.1000') + Decimal(str(i * 0.001))
            current_price = entry_price + Decimal(str((i % 3 - 1) * 0.0001))
            size = Decimal('1.0')
            
            unrealized_pnl = (current_price - entry_price) * size if side == "buy" else (entry_price - current_price) * size
            
            position = Position(
                position_id=f"POS_{i:03d}",
                account_id=account_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                timestamp=datetime.now()
            )
            positions.append(position)
        
        return positions
    
    async def get_account_info(self, account_id: str) -> Optional[AccountInfo]:
        """Get mock account info"""
        for account in self._mock_accounts:
            if account.account_id == account_id:
                return account
        return None
    
    async def get_all_accounts(self) -> List[AccountInfo]:
        """Get all mock accounts"""
        return self._mock_accounts.copy()
    
    async def get_open_positions(self, account_id: str) -> List[Position]:
        """Get mock positions for account"""
        return [p for p in self._mock_positions if p.account_id == account_id]
    
    async def update_account_balance(self, account_id: str, new_balance: Decimal) -> bool:
        """Update mock account balance"""
        for account in self._mock_accounts:
            if account.account_id == account_id:
                account.balance = new_balance
                account.equity = new_balance  # Simplified for mock
                return True
        return False
    
    async def get_accounts_by_prop_firm(self, prop_firm: str) -> List[AccountInfo]:
        """Get mock accounts by prop firm"""
        return [a for a in self._mock_accounts if a.prop_firm == prop_firm]