"""
OANDA Position Management & Modification System

Provides comprehensive control over open trading positions, enabling traders to actively
manage risk and optimize performance. Integrates with the risk management framework while
providing intuitive position control capabilities.
"""

from typing import List, Optional, Dict, Union, Any
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field
import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"


@dataclass
class PositionInfo:
    """Comprehensive position information"""
    position_id: str
    instrument: str
    side: PositionSide
    units: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pl: Decimal
    swap_charges: Decimal
    commission: Decimal
    margin_used: Decimal
    opened_at: datetime
    age_hours: float
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    trailing_stop_distance: Optional[Decimal] = None
    
    @property
    def pl_percentage(self) -> Decimal:
        """Calculate P&L as percentage of entry price"""
        if self.entry_price == 0:
            return Decimal('0')
        return (self.unrealized_pl / (self.units * self.entry_price)) * 100
    
    @property
    def risk_reward_ratio(self) -> Optional[Decimal]:
        """Calculate risk/reward ratio if SL and TP are set"""
        if not self.stop_loss or not self.take_profit:
            return None
            
        if self.side == PositionSide.LONG:
            risk = self.entry_price - self.stop_loss
            reward = self.take_profit - self.entry_price
        else:
            risk = self.stop_loss - self.entry_price
            reward = self.entry_price - self.take_profit
            
        if risk == 0:
            return None
        return reward / risk


class OandaPositionManager:
    """
    Main position management system for OANDA integration.
    Handles position data fetching, modification, and monitoring.
    """
    
    def __init__(self, client: Any, price_stream: Any):
        """
        Initialize position manager
        
        Args:
            client: OANDA API client
            price_stream: Price streaming manager for real-time prices
        """
        self.client = client
        self.price_stream = price_stream
        self.position_cache: Dict[str, PositionInfo] = {}
        self.trailing_stops: Dict[str, 'TrailingStopConfig'] = {}
        self._update_lock = asyncio.Lock()
        
    async def get_open_positions(self) -> List[PositionInfo]:
        """
        Fetch all open positions with current P&L
        
        Returns:
            List of PositionInfo objects for all open positions
        """
        try:
            async with self._update_lock:
                response = await self.client.get(
                    f"/v3/accounts/{self.client.account_id}/openPositions"
                )
                positions = []
                
                for pos_data in response.get('positions', []):
                    position = await self._parse_position_data(pos_data)
                    positions.append(position)
                    
                # Cache positions for quick access
                self.position_cache = {pos.position_id: pos for pos in positions}
                
                logger.info(f"Fetched {len(positions)} open positions")
                return positions
                
        except Exception as e:
            logger.error(f"Failed to fetch open positions: {e}")
            raise
            
    async def _parse_position_data(self, pos_data: Dict) -> PositionInfo:
        """
        Parse OANDA position data into PositionInfo
        
        Args:
            pos_data: Raw position data from OANDA API
            
        Returns:
            Parsed PositionInfo object
        """
        instrument = pos_data['instrument']
        
        # Determine if long or short position
        long_units = Decimal(pos_data.get('long', {}).get('units', '0'))
        short_units = Decimal(pos_data.get('short', {}).get('units', '0'))
        
        if long_units > 0:
            side = PositionSide.LONG
            units = long_units
            position_details = pos_data['long']
        else:
            side = PositionSide.SHORT
            units = abs(short_units)
            position_details = pos_data['short']
            
        entry_price = Decimal(position_details.get('averagePrice', '0'))
        unrealized_pl = Decimal(position_details.get('unrealizedPL', '0'))
        
        # Get current market price
        current_price = await self._get_current_price(instrument, side)
        
        # Calculate position age
        open_time = position_details.get('openTime', '')
        if open_time:
            opened_at = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
        else:
            opened_at = datetime.now(timezone.utc)
            
        age_hours = (datetime.now(timezone.utc) - opened_at).total_seconds() / 3600
        
        # Extract stop loss and take profit if present
        stop_loss = None
        take_profit = None
        trailing_stop_distance = None
        
        if 'stopLossOrder' in position_details:
            stop_loss = Decimal(position_details['stopLossOrder'].get('price', '0'))
            
        if 'takeProfitOrder' in position_details:
            take_profit = Decimal(position_details['takeProfitOrder'].get('price', '0'))
            
        if 'trailingStopLossOrder' in position_details:
            trailing_stop_distance = Decimal(
                position_details['trailingStopLossOrder'].get('distance', '0')
            )
        
        return PositionInfo(
            position_id=f"{instrument}_{side.value}",
            instrument=instrument,
            side=side,
            units=units,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pl=unrealized_pl,
            swap_charges=Decimal(pos_data.get('financing', '0')),
            commission=Decimal(pos_data.get('commission', '0')),
            margin_used=Decimal(pos_data.get('marginUsed', '0')),
            opened_at=opened_at,
            age_hours=age_hours,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_distance=trailing_stop_distance
        )
        
    async def _get_current_price(self, instrument: str, side: PositionSide) -> Decimal:
        """
        Get current market price for position valuation
        
        Args:
            instrument: Trading instrument
            side: Position side (for bid/ask selection)
            
        Returns:
            Current market price
        """
        try:
            # Get price from price stream if available
            if hasattr(self.price_stream, 'get_current_price'):
                price_data = await self.price_stream.get_current_price(instrument)
                if price_data:
                    # Use bid for short positions, ask for long positions
                    if side == PositionSide.SHORT:
                        return Decimal(price_data.get('bid', '0'))
                    else:
                        return Decimal(price_data.get('ask', '0'))
            
            # Fallback to pricing endpoint
            response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/pricing",
                params={"instruments": instrument}
            )
            
            price_data = response.get('prices', [{}])[0]
            if side == PositionSide.SHORT:
                return Decimal(price_data.get('closeoutBid', '0'))
            else:
                return Decimal(price_data.get('closeoutAsk', '0'))
                
        except Exception as e:
            logger.error(f"Failed to get current price for {instrument}: {e}")
            return Decimal('0')
            
    async def modify_stop_loss(self, position_id: str, stop_loss_price: Decimal) -> bool:
        """
        Modify stop loss for an open position
        
        Args:
            position_id: Position identifier
            stop_loss_price: New stop loss price
            
        Returns:
            True if modification successful, False otherwise
        """
        try:
            position = self.position_cache.get(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")
                
            # Validate stop loss price
            if not self._validate_stop_loss_price(position, stop_loss_price):
                raise ValueError(f"Invalid stop loss price {stop_loss_price}")
                
            # Get existing trade IDs for the position
            trades_response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/trades",
                params={"instrument": position.instrument, "state": "OPEN"}
            )
            
            trades = trades_response.get('trades', [])
            if not trades:
                raise ValueError(f"No open trades found for {position.instrument}")
                
            # Modify stop loss for each trade
            success_count = 0
            for trade in trades:
                trade_id = trade['id']
                
                modification_request = {
                    "stopLoss": {
                        "price": str(stop_loss_price),
                        "timeInForce": "GTC"
                    }
                }
                
                response = await self.client.put(
                    f"/v3/accounts/{self.client.account_id}/trades/{trade_id}/orders",
                    json=modification_request
                )
                
                if response.get('stopLossOrderTransaction'):
                    success_count += 1
                    
            # Update cache
            if success_count > 0:
                position.stop_loss = stop_loss_price
                logger.info(f"Successfully modified stop loss for {position_id} to {stop_loss_price}")
                return True
            else:
                logger.warning(f"No trades were modified for position {position_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to modify stop loss for {position_id}: {e}")
            return False
            
    async def modify_take_profit(self, position_id: str, take_profit_price: Decimal) -> bool:
        """
        Modify take profit for an open position
        
        Args:
            position_id: Position identifier
            take_profit_price: New take profit price
            
        Returns:
            True if modification successful, False otherwise
        """
        try:
            position = self.position_cache.get(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")
                
            # Validate take profit price
            if not self._validate_take_profit_price(position, take_profit_price):
                raise ValueError(f"Invalid take profit price {take_profit_price}")
                
            # Get existing trade IDs for the position
            trades_response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/trades",
                params={"instrument": position.instrument, "state": "OPEN"}
            )
            
            trades = trades_response.get('trades', [])
            if not trades:
                raise ValueError(f"No open trades found for {position.instrument}")
                
            # Modify take profit for each trade
            success_count = 0
            for trade in trades:
                trade_id = trade['id']
                
                modification_request = {
                    "takeProfit": {
                        "price": str(take_profit_price),
                        "timeInForce": "GTC"
                    }
                }
                
                response = await self.client.put(
                    f"/v3/accounts/{self.client.account_id}/trades/{trade_id}/orders",
                    json=modification_request
                )
                
                if response.get('takeProfitOrderTransaction'):
                    success_count += 1
                    
            # Update cache
            if success_count > 0:
                position.take_profit = take_profit_price
                logger.info(f"Successfully modified take profit for {position_id} to {take_profit_price}")
                return True
            else:
                logger.warning(f"No trades were modified for position {position_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to modify take profit for {position_id}: {e}")
            return False
            
    def _validate_stop_loss_price(self, position: PositionInfo, stop_loss_price: Decimal) -> bool:
        """
        Validate stop loss price for a position
        
        Args:
            position: Position information
            stop_loss_price: Proposed stop loss price
            
        Returns:
            True if valid, False otherwise
        """
        if position.side == PositionSide.LONG:
            # For long positions, stop loss must be below current price
            return stop_loss_price < position.current_price
        else:
            # For short positions, stop loss must be above current price
            return stop_loss_price > position.current_price
            
    def _validate_take_profit_price(self, position: PositionInfo, take_profit_price: Decimal) -> bool:
        """
        Validate take profit price for a position
        
        Args:
            position: Position information
            take_profit_price: Proposed take profit price
            
        Returns:
            True if valid, False otherwise
        """
        if position.side == PositionSide.LONG:
            # For long positions, take profit must be above current price
            return take_profit_price > position.current_price
        else:
            # For short positions, take profit must be below current price
            return take_profit_price < position.current_price
            
    async def get_position_by_instrument(self, instrument: str) -> Optional[PositionInfo]:
        """
        Get position information for a specific instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            PositionInfo if position exists, None otherwise
        """
        # First check cache
        for position in self.position_cache.values():
            if position.instrument == instrument:
                return position
                
        # If not in cache, refresh and check again
        await self.get_open_positions()
        
        for position in self.position_cache.values():
            if position.instrument == instrument:
                return position
                
        return None
        
    async def batch_modify_positions(
        self,
        modifications: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Batch modify multiple positions
        
        Args:
            modifications: List of modification requests
                Each dict should contain: position_id, stop_loss (optional), take_profit (optional)
                
        Returns:
            Dictionary mapping position_id to success status
        """
        results = {}
        
        for mod in modifications:
            position_id = mod.get('position_id')
            if not position_id:
                continue
                
            success = True
            
            # Modify stop loss if provided
            if 'stop_loss' in mod:
                sl_success = await self.modify_stop_loss(
                    position_id,
                    Decimal(str(mod['stop_loss']))
                )
                success = success and sl_success
                
            # Modify take profit if provided
            if 'take_profit' in mod:
                tp_success = await self.modify_take_profit(
                    position_id,
                    Decimal(str(mod['take_profit']))
                )
                success = success and tp_success
                
            results[position_id] = success
            
        return results