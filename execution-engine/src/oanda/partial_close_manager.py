"""
Partial Position Closing Manager for OANDA Integration

Handles partial position closing with FIFO compliance validation for US accounts.
Provides percentage-based and unit-based partial closing capabilities.
"""

from typing import Union, Dict, Optional, List, Any
from decimal import Decimal
import logging
import asyncio
from dataclasses import dataclass
from enum import Enum

from .position_manager import OandaPositionManager, PositionInfo, PositionSide

logger = logging.getLogger(__name__)


class CloseType(Enum):
    """Position close type enumeration"""
    FULL = "full"
    PARTIAL = "partial"
    EMERGENCY = "emergency"


@dataclass
class CloseResult:
    """Result of a position close operation"""
    position_id: str
    close_type: CloseType
    units_requested: Decimal
    units_closed: Decimal
    success: bool
    transaction_id: Optional[str] = None
    realized_pl: Optional[Decimal] = None
    error_message: Optional[str] = None


class PartialCloseManager:
    """
    Manages partial position closing with compliance validation.
    Ensures FIFO compliance for US accounts and provides various closing strategies.
    """
    
    def __init__(
        self,
        position_manager: OandaPositionManager,
        compliance_engine: Optional[Any] = None
    ):
        """
        Initialize partial close manager
        
        Args:
            position_manager: OANDA position manager instance
            compliance_engine: Optional compliance validation engine
        """
        self.position_manager = position_manager
        self.compliance_engine = compliance_engine
        self._close_lock = asyncio.Lock()
        
    async def partial_close_position(
        self,
        position_id: str,
        close_units: Union[Decimal, str],
        validate_fifo: bool = True
    ) -> CloseResult:
        """
        Close partial amount of a position
        
        Args:
            position_id: Position identifier
            close_units: Units to close (Decimal) or percentage string (e.g., "50%")
            validate_fifo: Whether to validate FIFO compliance
            
        Returns:
            CloseResult with operation details
        """
        try:
            async with self._close_lock:
                # Get position from cache
                position = self.position_manager.position_cache.get(position_id)
                if not position:
                    # Try refreshing cache
                    await self.position_manager.get_open_positions()
                    position = self.position_manager.position_cache.get(position_id)
                    
                    if not position:
                        return CloseResult(
                            position_id=position_id,
                            close_type=CloseType.PARTIAL,
                            units_requested=Decimal('0'),
                            units_closed=Decimal('0'),
                            success=False,
                            error_message=f"Position {position_id} not found"
                        )
                
                # Calculate units to close
                units_to_close = self._calculate_units_to_close(position, close_units)
                
                # Validate close amount
                if units_to_close <= 0:
                    return CloseResult(
                        position_id=position_id,
                        close_type=CloseType.PARTIAL,
                        units_requested=units_to_close,
                        units_closed=Decimal('0'),
                        success=False,
                        error_message=f"Invalid close amount: {units_to_close}"
                    )
                    
                if units_to_close > position.units:
                    return CloseResult(
                        position_id=position_id,
                        close_type=CloseType.PARTIAL,
                        units_requested=units_to_close,
                        units_closed=Decimal('0'),
                        success=False,
                        error_message=f"Close amount {units_to_close} exceeds position size {position.units}"
                    )
                
                # Check FIFO compliance if required
                if validate_fifo and await self._requires_fifo_compliance(position):
                    if self.compliance_engine:
                        fifo_result = await self.compliance_engine.validate_fifo_close(
                            position.instrument,
                            units_to_close
                        )
                        if not fifo_result.valid:
                            return CloseResult(
                                position_id=position_id,
                                close_type=CloseType.PARTIAL,
                                units_requested=units_to_close,
                                units_closed=Decimal('0'),
                                success=False,
                                error_message=f"FIFO violation: {fifo_result.reason}"
                            )
                
                # Determine if this is a full or partial close
                close_type = CloseType.FULL if units_to_close == position.units else CloseType.PARTIAL
                
                # Execute the close
                result = await self._execute_close(position, units_to_close)
                
                # Update position cache if successful
                if result.success:
                    if close_type == CloseType.FULL:
                        # Remove position from cache
                        del self.position_manager.position_cache[position_id]
                    else:
                        # Update remaining units
                        position.units -= units_to_close
                        
                    logger.info(
                        f"Successfully closed {units_to_close} units of {position_id} "
                        f"(Realized P&L: {result.realized_pl})"
                    )
                    
                result.close_type = close_type
                return result
                
        except Exception as e:
            logger.error(f"Failed to partially close position {position_id}: {e}")
            return CloseResult(
                position_id=position_id,
                close_type=CloseType.PARTIAL,
                units_requested=close_units if isinstance(close_units, Decimal) else Decimal('0'),
                units_closed=Decimal('0'),
                success=False,
                error_message=str(e)
            )
            
    def _calculate_units_to_close(
        self,
        position: PositionInfo,
        close_units: Union[Decimal, str]
    ) -> Decimal:
        """
        Calculate units to close based on input
        
        Args:
            position: Position information
            close_units: Units or percentage to close
            
        Returns:
            Decimal units to close
        """
        # Handle percentage-based closing
        if isinstance(close_units, str):
            close_units = close_units.strip()
            if close_units.endswith('%'):
                try:
                    percentage = Decimal(close_units[:-1]) / 100
                    return position.units * percentage
                except (ValueError, ArithmeticError):
                    logger.error(f"Invalid percentage value: {close_units}")
                    return Decimal('0')
            else:
                # Try to parse as decimal
                try:
                    return Decimal(close_units)
                except (ValueError, ArithmeticError):
                    logger.error(f"Invalid units value: {close_units}")
                    return Decimal('0')
        else:
            return Decimal(str(close_units))
            
    async def _requires_fifo_compliance(self, position: PositionInfo) -> bool:
        """
        Check if position requires FIFO compliance
        
        Args:
            position: Position information
            
        Returns:
            True if FIFO compliance required
        """
        # Check if compliance engine is available
        if not self.compliance_engine:
            return False
            
        # Check if account is US-regulated
        if hasattr(self.compliance_engine, 'is_us_account'):
            return await self.compliance_engine.is_us_account()
            
        return False
        
    async def _execute_close(
        self,
        position: PositionInfo,
        units_to_close: Decimal
    ) -> CloseResult:
        """
        Execute the actual position close with OANDA
        
        Args:
            position: Position information
            units_to_close: Units to close
            
        Returns:
            CloseResult with transaction details
        """
        try:
            # Build close request based on position side
            if position.side == PositionSide.LONG:
                close_request = {
                    "longUnits": str(units_to_close)
                }
            else:
                close_request = {
                    "shortUnits": str(units_to_close)
                }
                
            # Execute close with OANDA
            response = await self.position_manager.client.put(
                f"/v3/accounts/{self.position_manager.client.account_id}/positions/{position.instrument}/close",
                json=close_request
            )
            
            # Extract transaction details
            transaction = response.get('longOrderFillTransaction') or response.get('shortOrderFillTransaction')
            
            if transaction:
                transaction_id = transaction.get('id')
                realized_pl = Decimal(transaction.get('pl', '0'))
                units_closed = abs(Decimal(transaction.get('units', '0')))
                
                return CloseResult(
                    position_id=position.position_id,
                    close_type=CloseType.PARTIAL,
                    units_requested=units_to_close,
                    units_closed=units_closed,
                    success=True,
                    transaction_id=transaction_id,
                    realized_pl=realized_pl
                )
            else:
                return CloseResult(
                    position_id=position.position_id,
                    close_type=CloseType.PARTIAL,
                    units_requested=units_to_close,
                    units_closed=Decimal('0'),
                    success=False,
                    error_message="No transaction returned from close request"
                )
                
        except Exception as e:
            logger.error(f"Execute close failed for {position.position_id}: {e}")
            return CloseResult(
                position_id=position.position_id,
                close_type=CloseType.PARTIAL,
                units_requested=units_to_close,
                units_closed=Decimal('0'),
                success=False,
                error_message=str(e)
            )
            
    async def close_all_positions(
        self,
        filter_by_instrument: Optional[str] = None,
        emergency: bool = False
    ) -> Dict[str, CloseResult]:
        """
        Close all open positions
        
        Args:
            filter_by_instrument: Optional instrument filter
            emergency: Whether this is an emergency close (bypasses some validations)
            
        Returns:
            Dictionary mapping position_id to CloseResult
        """
        # Refresh position cache
        positions = await self.position_manager.get_open_positions()
        results = {}
        
        # Filter positions if needed
        if filter_by_instrument:
            positions = [p for p in positions if p.instrument == filter_by_instrument]
            
        logger.info(
            f"{'Emergency' if emergency else 'Bulk'} closing {len(positions)} positions"
            f"{f' for {filter_by_instrument}' if filter_by_instrument else ''}"
        )
        
        # Close positions concurrently for speed
        close_tasks = []
        for position in positions:
            # Skip FIFO validation in emergency mode
            validate_fifo = not emergency
            
            task = self.partial_close_position(
                position.position_id,
                position.units,
                validate_fifo=validate_fifo
            )
            close_tasks.append(task)
            
        # Wait for all closes to complete
        close_results = await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Process results
        for position, result in zip(positions, close_results):
            if isinstance(result, Exception):
                results[position.position_id] = CloseResult(
                    position_id=position.position_id,
                    close_type=CloseType.EMERGENCY if emergency else CloseType.FULL,
                    units_requested=position.units,
                    units_closed=Decimal('0'),
                    success=False,
                    error_message=str(result)
                )
            else:
                result.close_type = CloseType.EMERGENCY if emergency else CloseType.FULL
                results[position.position_id] = result
                
        # Log summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful
        total_pl = sum(r.realized_pl for r in results.values() if r.realized_pl)
        
        logger.info(
            f"Bulk close complete: {successful} successful, {failed} failed, "
            f"Total realized P&L: {total_pl}"
        )
        
        return results
        
    async def close_positions_by_criteria(
        self,
        min_profit: Optional[Decimal] = None,
        max_loss: Optional[Decimal] = None,
        min_age_hours: Optional[float] = None,
        instruments: Optional[List[str]] = None
    ) -> Dict[str, CloseResult]:
        """
        Close positions matching specific criteria
        
        Args:
            min_profit: Close positions with profit >= this amount
            max_loss: Close positions with loss >= this amount (as negative value)
            min_age_hours: Close positions older than this many hours
            instruments: Close positions for these instruments only
            
        Returns:
            Dictionary mapping position_id to CloseResult
        """
        # Refresh position cache
        positions = await self.position_manager.get_open_positions()
        positions_to_close = []
        
        for position in positions:
            should_close = False
            
            # Check instrument filter
            if instruments and position.instrument not in instruments:
                continue
                
            # Check profit threshold
            if min_profit is not None and position.unrealized_pl >= min_profit:
                should_close = True
                logger.info(
                    f"Position {position.position_id} marked for close: "
                    f"profit {position.unrealized_pl} >= {min_profit}"
                )
                
            # Check loss threshold
            if max_loss is not None and position.unrealized_pl <= max_loss:
                should_close = True
                logger.info(
                    f"Position {position.position_id} marked for close: "
                    f"loss {position.unrealized_pl} <= {max_loss}"
                )
                
            # Check age
            if min_age_hours is not None and position.age_hours >= min_age_hours:
                should_close = True
                logger.info(
                    f"Position {position.position_id} marked for close: "
                    f"age {position.age_hours:.1f}h >= {min_age_hours}h"
                )
                
            if should_close:
                positions_to_close.append(position)
                
        # Close selected positions
        results = {}
        for position in positions_to_close:
            result = await self.partial_close_position(
                position.position_id,
                position.units
            )
            results[position.position_id] = result
            
        logger.info(f"Closed {len(results)} positions based on criteria")
        return results