"""Real-time P&L tracking system."""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Set
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from .models import (
    TradePerformance, PerformanceSnapshot, PositionData, 
    MarketTick, PnLSnapshot, TradeStatus
)

logger = logging.getLogger(__name__)


class PnLCalculationEngine:
    """Core P&L calculation engine for positions and trades."""
    
    def __init__(self):
        self.position_cache = {}  # symbol -> current_price cache
        self.commission_rates = {
            'forex': Decimal('0.00002'),  # 2 pips per lot
            'indices': Decimal('0.01'),   # $1 per contract
            'commodities': Decimal('0.02') # $2 per contract
        }
    
    def calculate_unrealized_pnl(
        self, 
        position: PositionData, 
        current_price: Decimal
    ) -> Decimal:
        """Calculate unrealized P&L for open position."""
        try:
            position_size = position.position_size
            entry_price = position.entry_price
            
            # Calculate price difference
            if position_size > 0:  # Long position
                price_diff = current_price - entry_price
            else:  # Short position
                price_diff = entry_price - current_price
                position_size = abs(position_size)
            
            # Calculate P&L based on instrument type
            if self._is_forex_pair(position.symbol):
                # Forex: P&L = position_size * price_diff * contract_size
                contract_size = self._get_contract_size(position.symbol)
                pnl = position_size * price_diff * contract_size
            else:
                # Indices/Commodities: P&L = position_size * price_diff
                pnl = position_size * price_diff
            
            # Subtract estimated commission and swap
            pnl -= position.commission + position.swap
            
            return pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating unrealized P&L for {position.symbol}: {e}")
            return Decimal('0')
    
    def calculate_realized_pnl(self, trade: TradePerformance) -> Decimal:
        """Calculate realized P&L for closed trade."""
        if not trade.exit_price or trade.status != TradeStatus.CLOSED.value:
            return Decimal('0')
        
        try:
            position_size = trade.position_size
            entry_price = trade.entry_price
            exit_price = trade.exit_price
            
            # Calculate price difference
            if position_size > 0:  # Long position
                price_diff = exit_price - entry_price
            else:  # Short position  
                price_diff = entry_price - exit_price
                position_size = abs(position_size)
            
            # Calculate P&L based on instrument type
            if self._is_forex_pair(trade.symbol):
                contract_size = self._get_contract_size(trade.symbol)
                pnl = position_size * price_diff * contract_size
            else:
                pnl = position_size * price_diff
            
            # Subtract commission and swap
            pnl -= (trade.commission or Decimal('0')) + (trade.swap or Decimal('0'))
            
            # Calculate percentage return
            entry_value = abs(position_size * entry_price)
            pnl_percentage = (pnl / entry_value * 100) if entry_value > 0 else Decimal('0')
            
            return pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating realized P&L for trade {trade.trade_id}: {e}")
            return Decimal('0')
    
    def calculate_position_margin(self, position: PositionData) -> Decimal:
        """Calculate margin requirement for position."""
        try:
            position_size = abs(position.position_size)
            entry_price = position.entry_price
            
            # Get leverage for instrument type
            leverage = self._get_leverage(position.symbol)
            
            if self._is_forex_pair(position.symbol):
                contract_size = self._get_contract_size(position.symbol)
                notional_value = position_size * entry_price * contract_size
            else:
                notional_value = position_size * entry_price
            
            margin_required = notional_value / leverage
            return margin_required.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating margin for {position.symbol}: {e}")
            return Decimal('0')
    
    def _is_forex_pair(self, symbol: str) -> bool:
        """Check if symbol is a forex pair."""
        forex_pairs = [
            'EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD'
        ]
        return any(pair in symbol.upper() for pair in forex_pairs) and len(symbol) == 6
    
    def _get_contract_size(self, symbol: str) -> Decimal:
        """Get contract size for symbol."""
        if self._is_forex_pair(symbol):
            return Decimal('100000')  # Standard lot
        elif 'XAU' in symbol or 'GOLD' in symbol.upper():
            return Decimal('100')     # 100 ounces
        elif 'XAG' in symbol or 'SILVER' in symbol.upper():
            return Decimal('5000')    # 5000 ounces
        else:
            return Decimal('1')       # Default
    
    def _get_leverage(self, symbol: str) -> Decimal:
        """Get leverage for symbol."""
        if self._is_forex_pair(symbol):
            return Decimal('100')     # 1:100
        elif 'XAU' in symbol or 'GOLD' in symbol.upper():
            return Decimal('50')      # 1:50
        else:
            return Decimal('20')      # 1:20


class RealTimePnLTracker:
    """Real-time P&L tracking and updates."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.calculation_engine = PnLCalculationEngine()
        self.active_positions = {}  # account_id -> [positions]
        self.account_snapshots = {}  # account_id -> latest_snapshot
        self.websocket_connections = set()
        self.market_data_cache = {}  # symbol -> latest_tick
        self.update_frequency = 1  # seconds
        
    async def start_tracking(self):
        """Start real-time P&L tracking."""
        logger.info("Starting real-time P&L tracking...")
        
        # Load initial positions
        await self._load_open_positions()
        
        # Start background tasks
        asyncio.create_task(self._pnl_update_loop())
        asyncio.create_task(self._snapshot_cleanup_task())
        
    async def process_market_tick(self, tick: MarketTick):
        """Process incoming market data tick."""
        try:
            # Update market data cache
            self.market_data_cache[tick.symbol] = tick
            
            # Find accounts with positions in this symbol
            affected_accounts = []
            for account_id, positions in self.active_positions.items():
                if any(pos.symbol == tick.symbol for pos in positions):
                    affected_accounts.append(account_id)
            
            # Update P&L for affected accounts
            for account_id in affected_accounts:
                await self._update_account_pnl(account_id, tick.timestamp)
                
        except Exception as e:
            logger.error(f"Error processing market tick for {tick.symbol}: {e}")
    
    async def update_position(self, position: PositionData):
        """Update or add position data."""
        try:
            account_id = position.account_id
            
            if account_id not in self.active_positions:
                self.active_positions[account_id] = []
            
            # Find existing position or add new
            positions = self.active_positions[account_id]
            existing_pos = next(
                (pos for pos in positions if pos.position_id == position.position_id), 
                None
            )
            
            if existing_pos:
                # Update existing position
                positions[positions.index(existing_pos)] = position
            else:
                # Add new position
                positions.append(position)
            
            # Trigger immediate P&L update
            await self._update_account_pnl(account_id, datetime.utcnow())
            
            logger.info(f"Updated position {position.position_id} for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error updating position {position.position_id}: {e}")
    
    async def close_position(self, position_id: UUID, exit_price: Decimal, exit_time: datetime):
        """Close position and calculate final P&L."""
        try:
            # Find and remove position from active positions
            for account_id, positions in self.active_positions.items():
                position = next(
                    (pos for pos in positions if pos.position_id == position_id), 
                    None
                )
                
                if position:
                    # Calculate final P&L
                    realized_pnl = self.calculation_engine.calculate_unrealized_pnl(
                        position, exit_price
                    )
                    
                    # Update trade record in database
                    trade = self.db.query(TradePerformance).filter(
                        TradePerformance.trade_id == position_id
                    ).first()
                    
                    if trade:
                        trade.exit_price = exit_price
                        trade.exit_time = exit_time
                        trade.pnl = realized_pnl
                        trade.status = TradeStatus.CLOSED.value
                        trade.trade_duration_seconds = int(
                            (exit_time - trade.entry_time).total_seconds()
                        )
                        
                        # Calculate percentage return
                        entry_value = abs(trade.position_size * trade.entry_price)
                        if entry_value > 0:
                            trade.pnl_percentage = realized_pnl / entry_value * 100
                        
                        self.db.commit()
                    
                    # Remove from active positions
                    positions.remove(position)
                    
                    # Update account P&L
                    await self._update_account_pnl(account_id, exit_time)
                    
                    logger.info(f"Closed position {position_id} with P&L: {realized_pnl}")
                    break
                    
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
    
    async def get_account_pnl(self, account_id: UUID) -> Optional[PnLSnapshot]:
        """Get current P&L snapshot for account."""
        try:
            # Get latest snapshot
            latest_snapshot = self.db.query(PerformanceSnapshot).filter(
                PerformanceSnapshot.account_id == account_id
            ).order_by(desc(PerformanceSnapshot.snapshot_time)).first()
            
            if not latest_snapshot:
                return None
            
            # Calculate current unrealized P&L
            positions = self.active_positions.get(account_id, [])
            current_unrealized = Decimal('0')
            
            for position in positions:
                if position.symbol in self.market_data_cache:
                    tick = self.market_data_cache[position.symbol]
                    current_price = (tick.bid_price + tick.ask_price) / 2
                    unrealized_pnl = self.calculation_engine.calculate_unrealized_pnl(
                        position, current_price
                    )
                    current_unrealized += unrealized_pnl
            
            total_pnl = latest_snapshot.realized_pnl + current_unrealized
            
            # Calculate daily change
            daily_change = total_pnl - latest_snapshot.daily_pnl
            daily_change_pct = (daily_change / latest_snapshot.balance * 100) if latest_snapshot.balance > 0 else Decimal('0')
            
            return PnLSnapshot(
                account_id=account_id,
                timestamp=datetime.utcnow(),
                balance=latest_snapshot.balance,
                equity=latest_snapshot.balance + current_unrealized,
                realized_pnl=latest_snapshot.realized_pnl,
                unrealized_pnl=current_unrealized,
                total_pnl=total_pnl,
                daily_change=daily_change,
                daily_change_percentage=daily_change_pct,
                open_positions=len(positions)
            )
            
        except Exception as e:
            logger.error(f"Error getting P&L for account {account_id}: {e}")
            return None
    
    async def get_aggregate_pnl(self, account_ids: List[UUID]) -> PnLSnapshot:
        """Get aggregate P&L across multiple accounts."""
        try:
            total_balance = Decimal('0')
            total_equity = Decimal('0')
            total_realized = Decimal('0')
            total_unrealized = Decimal('0')
            total_positions = 0
            
            for account_id in account_ids:
                snapshot = await self.get_account_pnl(account_id)
                if snapshot:
                    total_balance += snapshot.balance
                    total_equity += snapshot.equity
                    total_realized += snapshot.realized_pnl
                    total_unrealized += snapshot.unrealized_pnl
                    total_positions += snapshot.open_positions
            
            total_pnl = total_realized + total_unrealized
            
            # Use first account for aggregate display
            primary_account = account_ids[0] if account_ids else UUID('00000000-0000-0000-0000-000000000000')
            
            return PnLSnapshot(
                account_id=primary_account,
                timestamp=datetime.utcnow(),
                balance=total_balance,
                equity=total_equity,
                realized_pnl=total_realized,
                unrealized_pnl=total_unrealized,
                total_pnl=total_pnl,
                daily_change=Decimal('0'),  # Would need historical data
                daily_change_percentage=Decimal('0'),
                open_positions=total_positions
            )
            
        except Exception as e:
            logger.error(f"Error calculating aggregate P&L: {e}")
            return PnLSnapshot(
                account_id=UUID('00000000-0000-0000-0000-000000000000'),
                timestamp=datetime.utcnow(),
                balance=Decimal('0'),
                equity=Decimal('0'),
                realized_pnl=Decimal('0'),
                unrealized_pnl=Decimal('0'),
                total_pnl=Decimal('0'),
                daily_change=Decimal('0'),
                daily_change_percentage=Decimal('0'),
                open_positions=0
            )
    
    async def _load_open_positions(self):
        """Load open positions from database."""
        try:
            open_trades = self.db.query(TradePerformance).filter(
                TradePerformance.status == TradeStatus.OPEN.value
            ).all()
            
            for trade in open_trades:
                position = PositionData(
                    position_id=trade.trade_id,
                    account_id=trade.account_id,
                    symbol=trade.symbol,
                    position_size=trade.position_size,
                    entry_price=trade.entry_price,
                    current_price=trade.entry_price,  # Will be updated by market data
                    unrealized_pnl=Decimal('0'),
                    commission=trade.commission or Decimal('0'),
                    swap=trade.swap or Decimal('0'),
                    margin_used=self.calculation_engine.calculate_position_margin(
                        PositionData(
                            position_id=trade.trade_id,
                            account_id=trade.account_id,
                            symbol=trade.symbol,
                            position_size=trade.position_size,
                            entry_price=trade.entry_price,
                            current_price=trade.entry_price,
                            unrealized_pnl=Decimal('0')
                        )
                    )
                )
                
                if trade.account_id not in self.active_positions:
                    self.active_positions[trade.account_id] = []
                
                self.active_positions[trade.account_id].append(position)
            
            logger.info(f"Loaded {len(open_trades)} open positions")
            
        except Exception as e:
            logger.error(f"Error loading open positions: {e}")
    
    async def _pnl_update_loop(self):
        """Main P&L update loop."""
        while True:
            try:
                # Update P&L for all active accounts
                for account_id in self.active_positions.keys():
                    await self._update_account_pnl(account_id, datetime.utcnow())
                
                # Wait for next update
                await asyncio.sleep(self.update_frequency)
                
            except Exception as e:
                logger.error(f"Error in P&L update loop: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _update_account_pnl(self, account_id: UUID, timestamp: datetime):
        """Update P&L snapshot for specific account."""
        try:
            positions = self.active_positions.get(account_id, [])
            
            # Calculate current unrealized P&L
            total_unrealized = Decimal('0')
            total_margin = Decimal('0')
            
            for position in positions:
                if position.symbol in self.market_data_cache:
                    tick = self.market_data_cache[position.symbol]
                    current_price = (tick.bid_price + tick.ask_price) / 2
                    
                    unrealized_pnl = self.calculation_engine.calculate_unrealized_pnl(
                        position, current_price
                    )
                    position.current_price = current_price
                    position.unrealized_pnl = unrealized_pnl
                    
                    total_unrealized += unrealized_pnl
                    total_margin += position.margin_used
            
            # Get latest snapshot for baseline
            latest_snapshot = self.db.query(PerformanceSnapshot).filter(
                PerformanceSnapshot.account_id == account_id
            ).order_by(desc(PerformanceSnapshot.snapshot_time)).first()
            
            if latest_snapshot:
                balance = latest_snapshot.balance
                realized_pnl = latest_snapshot.realized_pnl
            else:
                # Initialize new account
                balance = Decimal('100000')  # Default starting balance
                realized_pnl = Decimal('0')
            
            # Create new snapshot
            snapshot = PerformanceSnapshot(
                account_id=account_id,
                snapshot_time=timestamp,
                balance=balance,
                equity=balance + total_unrealized,
                margin_used=total_margin,
                free_margin=balance + total_unrealized - total_margin,
                open_positions=len(positions),
                realized_pnl=realized_pnl,
                unrealized_pnl=total_unrealized,
                daily_pnl=realized_pnl + total_unrealized,
                weekly_pnl=realized_pnl + total_unrealized,
                monthly_pnl=realized_pnl + total_unrealized
            )
            
            self.db.add(snapshot)
            self.db.commit()
            
            # Cache latest snapshot
            self.account_snapshots[account_id] = snapshot
            
            # Broadcast to WebSocket clients
            await self._broadcast_pnl_update(account_id, snapshot)
            
        except Exception as e:
            logger.error(f"Error updating P&L for account {account_id}: {e}")
    
    async def _broadcast_pnl_update(self, account_id: UUID, snapshot: PerformanceSnapshot):
        """Broadcast P&L update to WebSocket clients."""
        try:
            message = {
                'channel': 'pnl',
                'account_id': str(account_id),
                'data': {
                    'balance': float(snapshot.balance),
                    'equity': float(snapshot.equity),
                    'realized_pnl': float(snapshot.realized_pnl),
                    'unrealized_pnl': float(snapshot.unrealized_pnl),
                    'daily_pnl': float(snapshot.daily_pnl),
                    'open_positions': snapshot.open_positions,
                    'timestamp': snapshot.snapshot_time.isoformat()
                }
            }
            
            # Would integrate with WebSocket server here
            logger.debug(f"Broadcasting P&L update for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting P&L update: {e}")
    
    async def _snapshot_cleanup_task(self):
        """Clean up old snapshots to manage storage."""
        while True:
            try:
                # Keep only latest 1000 snapshots per account
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                
                # Delete old snapshots
                deleted_count = self.db.query(PerformanceSnapshot).filter(
                    PerformanceSnapshot.snapshot_time < cutoff_time
                ).delete()
                
                if deleted_count > 0:
                    self.db.commit()
                    logger.info(f"Cleaned up {deleted_count} old performance snapshots")
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in snapshot cleanup: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes before retry