"""
Trailing Stop Loss Management System for OANDA Integration

Provides dynamic trailing stop functionality with distance-based and percentage-based
trailing stops, activation levels, and real-time monitoring.
"""

from typing import Dict, Optional, List, Any
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import logging

from .position_manager import OandaPositionManager, PositionInfo, PositionSide

logger = logging.getLogger(__name__)


class TrailingType(Enum):
    """Trailing stop type enumeration"""
    DISTANCE = "distance"  # Fixed pip distance
    PERCENTAGE = "percentage"  # Percentage of price
    ATR = "atr"  # ATR-based (future enhancement)


@dataclass
class TrailingStopConfig:
    """Configuration for a trailing stop"""
    position_id: str
    instrument: str
    side: PositionSide
    trailing_type: TrailingType
    trail_value: Decimal  # Distance in pips or percentage
    activation_level: Optional[Decimal] = None  # Price level to start trailing
    current_stop: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None  # For long positions
    lowest_price: Optional[Decimal] = None  # For short positions
    is_active: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: Optional[datetime] = None
    update_count: int = 0
    
    @property
    def trail_distance_pips(self) -> Decimal:
        """Get trail distance in pips"""
        if self.trailing_type == TrailingType.DISTANCE:
            return self.trail_value
        elif self.trailing_type == TrailingType.PERCENTAGE:
            # Convert percentage to approximate pip distance
            if self.highest_price and self.side == PositionSide.LONG:
                return self.highest_price * self.trail_value / 100
            elif self.lowest_price and self.side == PositionSide.SHORT:
                return self.lowest_price * self.trail_value / 100
        return Decimal('0')


class TrailingStopManager:
    """
    Manages trailing stops for open positions.
    Monitors price movements and automatically adjusts stop losses.
    """
    
    def __init__(
        self,
        position_manager: OandaPositionManager,
        update_interval: int = 5
    ):
        """
        Initialize trailing stop manager
        
        Args:
            position_manager: OANDA position manager instance
            update_interval: Seconds between price checks
        """
        self.position_manager = position_manager
        self.update_interval = update_interval
        self.trailing_stops: Dict[str, TrailingStopConfig] = {}
        self.is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._update_lock = asyncio.Lock()
        
    async def set_trailing_stop(
        self,
        position_id: str,
        trail_value: Decimal,
        trailing_type: TrailingType = TrailingType.DISTANCE,
        activation_level: Optional[Decimal] = None
    ) -> bool:
        """
        Set trailing stop for a position
        
        Args:
            position_id: Position identifier
            trail_value: Trail distance in pips or percentage
            trailing_type: Type of trailing stop
            activation_level: Optional price level to activate trailing
            
        Returns:
            True if trailing stop set successfully
        """
        try:
            async with self._update_lock:
                # Get position information
                position = self.position_manager.position_cache.get(position_id)
                if not position:
                    # Try refreshing cache
                    await self.position_manager.get_open_positions()
                    position = self.position_manager.position_cache.get(position_id)
                    
                if not position:
                    logger.error(f"Position {position_id} not found")
                    return False
                    
                # Calculate initial stop level
                initial_stop = self._calculate_initial_stop(
                    position,
                    trail_value,
                    trailing_type
                )
                
                # Determine if trailing should be active immediately
                is_active = activation_level is None
                if activation_level:
                    if position.side == PositionSide.LONG:
                        is_active = position.current_price >= activation_level
                    else:
                        is_active = position.current_price <= activation_level
                        
                # Create trailing stop configuration
                trailing_config = TrailingStopConfig(
                    position_id=position_id,
                    instrument=position.instrument,
                    side=position.side,
                    trailing_type=trailing_type,
                    trail_value=trail_value,
                    activation_level=activation_level,
                    current_stop=initial_stop if is_active else None,
                    highest_price=position.current_price if position.side == PositionSide.LONG else None,
                    lowest_price=position.current_price if position.side == PositionSide.SHORT else None,
                    is_active=is_active
                )
                
                self.trailing_stops[position_id] = trailing_config
                
                # Set initial stop loss if active
                if is_active and initial_stop:
                    success = await self.position_manager.modify_stop_loss(
                        position_id,
                        initial_stop
                    )
                    if not success:
                        logger.warning(f"Failed to set initial stop for {position_id}")
                        
                # Start monitoring if not already running
                if not self.is_monitoring:
                    self._monitor_task = asyncio.create_task(self._monitor_trailing_stops())
                    
                logger.info(
                    f"Set {'active' if is_active else 'pending'} trailing stop for {position_id} "
                    f"with {trail_value} {trailing_type.value} trail"
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to set trailing stop for {position_id}: {e}")
            return False
            
    def _calculate_initial_stop(
        self,
        position: PositionInfo,
        trail_value: Decimal,
        trailing_type: TrailingType
    ) -> Decimal:
        """
        Calculate initial stop loss level
        
        Args:
            position: Position information
            trail_value: Trail value
            trailing_type: Type of trailing stop
            
        Returns:
            Initial stop loss price
        """
        if trailing_type == TrailingType.DISTANCE:
            # Distance is in pips, convert to price
            pip_value = self._get_pip_value(position.instrument)
            distance = trail_value * pip_value
            
            if position.side == PositionSide.LONG:
                return position.current_price - distance
            else:
                return position.current_price + distance
                
        elif trailing_type == TrailingType.PERCENTAGE:
            # Percentage of current price
            distance = position.current_price * trail_value / 100
            
            if position.side == PositionSide.LONG:
                return position.current_price - distance
            else:
                return position.current_price + distance
                
        return position.current_price
        
    def _get_pip_value(self, instrument: str) -> Decimal:
        """
        Get pip value for an instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            Pip value (typically 0.0001 for most pairs, 0.01 for JPY pairs)
        """
        # Check if JPY pair
        if 'JPY' in instrument:
            return Decimal('0.01')
        else:
            return Decimal('0.0001')
            
    async def _monitor_trailing_stops(self):
        """Monitor and update trailing stops"""
        self.is_monitoring = True
        logger.info("Started trailing stop monitoring")
        
        try:
            while self.trailing_stops:
                await asyncio.sleep(self.update_interval)
                
                # Update all trailing stops
                async with self._update_lock:
                    for position_id in list(self.trailing_stops.keys()):
                        try:
                            await self._update_trailing_stop(position_id)
                        except Exception as e:
                            logger.error(f"Error updating trailing stop for {position_id}: {e}")
                            
        except asyncio.CancelledError:
            logger.info("Trailing stop monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in trailing stop monitoring: {e}")
        finally:
            self.is_monitoring = False
            logger.info("Stopped trailing stop monitoring")
            
    async def _update_trailing_stop(self, position_id: str):
        """
        Update trailing stop based on price movement
        
        Args:
            position_id: Position identifier
        """
        config = self.trailing_stops.get(position_id)
        if not config:
            return
            
        # Get current position
        position = self.position_manager.position_cache.get(position_id)
        if not position:
            # Position closed, remove trailing stop
            logger.info(f"Position {position_id} closed, removing trailing stop")
            del self.trailing_stops[position_id]
            return
            
        current_price = position.current_price
        
        # Check activation if not yet active
        if not config.is_active and config.activation_level:
            if position.side == PositionSide.LONG:
                if current_price >= config.activation_level:
                    config.is_active = True
                    config.current_stop = self._calculate_initial_stop(
                        position,
                        config.trail_value,
                        config.trailing_type
                    )
                    logger.info(f"Trailing stop activated for {position_id} at {current_price}")
            else:
                if current_price <= config.activation_level:
                    config.is_active = True
                    config.current_stop = self._calculate_initial_stop(
                        position,
                        config.trail_value,
                        config.trailing_type
                    )
                    logger.info(f"Trailing stop activated for {position_id} at {current_price}")
                    
        # Update trailing stop if active
        if config.is_active:
            needs_update = False
            new_stop_price = config.current_stop
            
            if position.side == PositionSide.LONG:
                # Update highest price seen
                if not config.highest_price or current_price > config.highest_price:
                    config.highest_price = current_price
                    
                    # Calculate new stop based on trailing type
                    if config.trailing_type == TrailingType.DISTANCE:
                        pip_value = self._get_pip_value(position.instrument)
                        new_stop_price = current_price - (config.trail_value * pip_value)
                    elif config.trailing_type == TrailingType.PERCENTAGE:
                        new_stop_price = current_price * (1 - config.trail_value / 100)
                        
                    # Only update if new stop is higher than current
                    if not config.current_stop or new_stop_price > config.current_stop:
                        needs_update = True
                        
            else:  # SHORT position
                # Update lowest price seen
                if not config.lowest_price or current_price < config.lowest_price:
                    config.lowest_price = current_price
                    
                    # Calculate new stop based on trailing type
                    if config.trailing_type == TrailingType.DISTANCE:
                        pip_value = self._get_pip_value(position.instrument)
                        new_stop_price = current_price + (config.trail_value * pip_value)
                    elif config.trailing_type == TrailingType.PERCENTAGE:
                        new_stop_price = current_price * (1 + config.trail_value / 100)
                        
                    # Only update if new stop is lower than current
                    if not config.current_stop or new_stop_price < config.current_stop:
                        needs_update = True
                        
            # Update stop loss if needed
            if needs_update and new_stop_price != config.current_stop:
                success = await self.position_manager.modify_stop_loss(position_id, new_stop_price)
                if success:
                    config.current_stop = new_stop_price
                    config.last_updated = datetime.now(timezone.utc)
                    config.update_count += 1
                    logger.info(
                        f"Updated trailing stop for {position_id} to {new_stop_price:.5f} "
                        f"(update #{config.update_count})"
                    )
                    
    async def remove_trailing_stop(self, position_id: str) -> bool:
        """
        Remove trailing stop for a position
        
        Args:
            position_id: Position identifier
            
        Returns:
            True if removed successfully
        """
        try:
            async with self._update_lock:
                if position_id in self.trailing_stops:
                    del self.trailing_stops[position_id]
                    logger.info(f"Removed trailing stop for {position_id}")
                    
                    # Stop monitoring if no more trailing stops
                    if not self.trailing_stops and self._monitor_task:
                        self._monitor_task.cancel()
                        
                    return True
                else:
                    logger.warning(f"No trailing stop found for {position_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to remove trailing stop for {position_id}: {e}")
            return False
            
    async def get_trailing_stop_status(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of trailing stop for a position
        
        Args:
            position_id: Position identifier
            
        Returns:
            Dictionary with trailing stop status or None
        """
        config = self.trailing_stops.get(position_id)
        if not config:
            return None
            
        return {
            'position_id': config.position_id,
            'instrument': config.instrument,
            'side': config.side.value,
            'trailing_type': config.trailing_type.value,
            'trail_value': float(config.trail_value),
            'activation_level': float(config.activation_level) if config.activation_level else None,
            'current_stop': float(config.current_stop) if config.current_stop else None,
            'highest_price': float(config.highest_price) if config.highest_price else None,
            'lowest_price': float(config.lowest_price) if config.lowest_price else None,
            'is_active': config.is_active,
            'created_at': config.created_at.isoformat(),
            'last_updated': config.last_updated.isoformat() if config.last_updated else None,
            'update_count': config.update_count
        }
        
    async def list_all_trailing_stops(self) -> List[Dict[str, Any]]:
        """
        List all active trailing stops
        
        Returns:
            List of trailing stop status dictionaries
        """
        stops = []
        for position_id in self.trailing_stops:
            status = await self.get_trailing_stop_status(position_id)
            if status:
                stops.append(status)
        return stops
        
    async def stop_monitoring(self):
        """Stop the monitoring task"""
        if self._monitor_task:
            self._monitor_task.cancel()
            await asyncio.gather(self._monitor_task, return_exceptions=True)
            self._monitor_task = None
            self.is_monitoring = False
            logger.info("Trailing stop monitoring stopped")