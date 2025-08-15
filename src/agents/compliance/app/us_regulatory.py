"""
US Regulatory Compliance Module

Implements NFA regulatory compliance for US-based retail traders:
- FIFO (First In, First Out) position management
- Anti-hedging enforcement
- Leverage limit validation
- Comprehensive audit logging
"""

from collections import defaultdict, deque
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceViolationType(Enum):
    FIFO_VIOLATION = "fifo_violation"
    HEDGING_VIOLATION = "hedging_violation" 
    LEVERAGE_VIOLATION = "leverage_violation"
    POSITION_LIMIT_VIOLATION = "position_limit_violation"


@dataclass
class ComplianceResult:
    """Result of compliance validation"""
    valid: bool
    violation_type: Optional[ComplianceViolationType] = None
    reason: Optional[str] = None
    suggested_action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Position:
    """Trading position for FIFO tracking"""
    id: str
    instrument: str
    units: int
    side: str  # 'BUY' or 'SELL'
    entry_price: Decimal
    timestamp: datetime
    account_id: str


@dataclass
class OrderRequest:
    """Order request for validation"""
    instrument: str
    units: int
    side: str  # 'BUY' or 'SELL'
    order_type: str  # 'MARKET', 'LIMIT', 'CLOSE'
    price: Optional[Decimal] = None
    account_id: str = ""
    account_region: str = "US"


class FIFOComplianceEngine:
    """FIFO compliance engine for US accounts"""
    
    def __init__(self):
        self.position_queues: Dict[str, deque] = defaultdict(deque)  # instrument -> queue of positions
        self.audit_log: List[Dict[str, Any]] = []
    
    async def validate_order(self, order: OrderRequest) -> ComplianceResult:
        """Validate order against FIFO rules"""
        if order.account_region != 'US':
            return ComplianceResult(valid=True)
            
        try:
            # Check for FIFO violations
            if order.order_type == 'CLOSE':
                result = await self.validate_fifo_close(order)
            elif order.order_type in ['MARKET', 'LIMIT']:
                result = await self.validate_new_position(order)
            else:
                result = ComplianceResult(valid=True)
                
            # Log compliance check
            self._log_compliance_check(order, result)
            return result
            
        except Exception as e:
            logger.error(f"FIFO validation error: {e}")
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.FIFO_VIOLATION,
                reason=f"FIFO validation error: {str(e)}"
            )
    
    async def validate_fifo_close(self, order: OrderRequest) -> ComplianceResult:
        """Ensure closes follow FIFO order"""
        position_queue = self.position_queues[f"{order.account_id}:{order.instrument}"]
        
        if not position_queue:
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.FIFO_VIOLATION,
                reason="No positions to close for FIFO compliance"
            )
            
        # Find positions that match the closing direction
        matching_positions = [p for p in position_queue if p.side != order.side]
        
        if not matching_positions:
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.FIFO_VIOLATION,
                reason=f"No {self._opposite_side(order.side)} positions to close"
            )
            
        # Must close oldest position first
        oldest_position = matching_positions[0]
        total_available = sum(p.units for p in matching_positions)
        
        if abs(order.units) > total_available:
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.FIFO_VIOLATION,
                reason=f"Insufficient position size: trying to close {abs(order.units)} units, only {total_available} available"
            )
            
        return ComplianceResult(
            valid=True,
            suggested_action=f"Will close oldest position first (opened at {oldest_position.timestamp})"
        )
    
    async def validate_new_position(self, order: OrderRequest) -> ComplianceResult:
        """Validate new position doesn't violate FIFO principles"""
        # For new positions, just log for tracking
        return ComplianceResult(valid=True)
    
    def auto_select_fifo_positions(self, account_id: str, instrument: str, 
                                 units_to_close: int, closing_side: str) -> List[Position]:
        """Automatically select positions for FIFO-compliant closing"""
        position_queue = self.position_queues[f"{account_id}:{instrument}"]
        
        # Find positions that can be closed (opposite side)
        target_side = self._opposite_side(closing_side)
        closeable_positions = [p for p in position_queue if p.side == target_side]
        
        selected_positions = []
        remaining_units = abs(units_to_close)
        
        for position in closeable_positions:
            if remaining_units <= 0:
                break
                
            if position.units <= remaining_units:
                # Close entire position
                selected_positions.append(position)
                remaining_units -= position.units
            else:
                # Partial close
                partial_position = Position(
                    id=f"{position.id}_partial",
                    instrument=position.instrument,
                    units=remaining_units,
                    side=position.side,
                    entry_price=position.entry_price,
                    timestamp=position.timestamp,
                    account_id=position.account_id
                )
                selected_positions.append(partial_position)
                remaining_units = 0
                
        return selected_positions
    
    def add_position(self, position: Position):
        """Add position to FIFO queue"""
        queue_key = f"{position.account_id}:{position.instrument}"
        self.position_queues[queue_key].append(position)
        
        self._log_position_update(position, "ADDED")
    
    def remove_position(self, account_id: str, instrument: str, position_id: str):
        """Remove position from FIFO queue"""
        queue_key = f"{account_id}:{instrument}"
        position_queue = self.position_queues[queue_key]
        
        # Find and remove position
        for i, position in enumerate(position_queue):
            if position.id == position_id:
                removed_position = position_queue[i]
                del position_queue[i]
                self._log_position_update(removed_position, "REMOVED")
                break
    
    def update_position_size(self, account_id: str, instrument: str, 
                           position_id: str, new_units: int):
        """Update position size (for partial closes)"""
        queue_key = f"{account_id}:{instrument}"
        position_queue = self.position_queues[queue_key]
        
        for position in position_queue:
            if position.id == position_id:
                old_units = position.units
                position.units = new_units
                self._log_position_update(position, f"UPDATED_SIZE_{old_units}_to_{new_units}")
                break
    
    def _opposite_side(self, side: str) -> str:
        """Get opposite trading side"""
        return 'SELL' if side == 'BUY' else 'BUY'
    
    def _log_compliance_check(self, order: OrderRequest, result: ComplianceResult):
        """Log compliance check for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'check_type': 'FIFO_COMPLIANCE',
            'order': {
                'instrument': order.instrument,
                'units': order.units,
                'side': order.side,
                'order_type': order.order_type,
                'account_id': order.account_id
            },
            'result': {
                'valid': result.valid,
                'violation_type': result.violation_type.value if result.violation_type else None,
                'reason': result.reason
            }
        }
        self.audit_log.append(log_entry)
        logger.info(f"FIFO compliance check: {log_entry}")
    
    def _log_position_update(self, position: Position, action: str):
        """Log position updates for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'position': {
                'id': position.id,
                'instrument': position.instrument,
                'units': position.units,
                'side': position.side,
                'account_id': position.account_id
            }
        }
        self.audit_log.append(log_entry)


class AntiHedgingValidator:
    """Anti-hedging validation for US accounts"""
    
    def __init__(self, fifo_engine: FIFOComplianceEngine):
        self.fifo_engine = fifo_engine
        self.audit_log: List[Dict[str, Any]] = []
    
    async def validate_no_hedging(self, order: OrderRequest) -> ComplianceResult:
        """Prevent hedging for US accounts"""
        if order.account_region != 'US':
            return ComplianceResult(valid=True)
            
        try:
            # Get existing positions
            queue_key = f"{order.account_id}:{order.instrument}"
            existing_positions = list(self.fifo_engine.position_queues[queue_key])
            
            # Check for opposite direction positions
            for position in existing_positions:
                if self.would_create_hedge(position, order):
                    result = ComplianceResult(
                        valid=False,
                        violation_type=ComplianceViolationType.HEDGING_VIOLATION,
                        reason=f"Hedging violation: Cannot open {order.side} position while {position.side} position exists",
                        suggested_action=f"Close existing {position.side} position first or modify order to same direction"
                    )
                    self._log_hedging_check(order, result, position)
                    return result
                    
            result = ComplianceResult(valid=True)
            self._log_hedging_check(order, result)
            return result
            
        except Exception as e:
            logger.error(f"Anti-hedging validation error: {e}")
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.HEDGING_VIOLATION,
                reason=f"Anti-hedging validation error: {str(e)}"
            )
    
    def would_create_hedge(self, position: Position, order: OrderRequest) -> bool:
        """Check if order would create a hedge"""
        return (
            position.instrument == order.instrument and
            position.side != order.side and
            position.units > 0 and
            order.order_type in ['MARKET', 'LIMIT']  # Only check for new positions
        )
    
    def _log_hedging_check(self, order: OrderRequest, result: ComplianceResult, 
                          conflicting_position: Optional[Position] = None):
        """Log hedging check for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'check_type': 'ANTI_HEDGING',
            'order': {
                'instrument': order.instrument,
                'units': order.units,
                'side': order.side,
                'order_type': order.order_type,
                'account_id': order.account_id
            },
            'result': {
                'valid': result.valid,
                'violation_type': result.violation_type.value if result.violation_type else None,
                'reason': result.reason
            },
            'conflicting_position': {
                'id': conflicting_position.id,
                'side': conflicting_position.side,
                'units': conflicting_position.units
            } if conflicting_position else None
        }
        self.audit_log.append(log_entry)
        logger.info(f"Anti-hedging check: {log_entry}")


class LeverageLimitValidator:
    """Leverage limit enforcement for US accounts"""
    
    def __init__(self):
        self.major_pairs = {
            'EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF', 
            'USD_CAD', 'AUD_USD', 'NZD_USD'
        }
        self.leverage_limits = {
            'major': Decimal('50'),  # 50:1
            'minor': Decimal('20')   # 20:1
        }
        self.audit_log: List[Dict[str, Any]] = []
    
    async def validate_leverage(self, order: OrderRequest, 
                              account_balance: Decimal, 
                              current_margin_used: Decimal = Decimal('0')) -> ComplianceResult:
        """Validate order doesn't exceed leverage limits"""
        if order.account_region != 'US':
            return ComplianceResult(valid=True)
            
        try:
            # Calculate effective leverage
            pair_type = 'major' if order.instrument in self.major_pairs else 'minor'
            max_leverage = self.leverage_limits[pair_type]
            
            # Calculate position value (assuming price is provided or 1.0)
            price = order.price if order.price else Decimal('1.0')
            position_value = abs(order.units) * price
            required_margin = position_value / max_leverage
            
            # Calculate available margin
            available_margin = account_balance - current_margin_used
            
            if required_margin > available_margin:
                result = ComplianceResult(
                    valid=False,
                    violation_type=ComplianceViolationType.LEVERAGE_VIOLATION,
                    reason=f"Leverage limit exceeded: {pair_type} pairs limited to {max_leverage}:1 leverage. Required margin: {required_margin}, Available: {available_margin}",
                    suggested_action=f"Reduce position size to maximum {int(available_margin * max_leverage / price)} units"
                )
            else:
                result = ComplianceResult(
                    valid=True,
                    metadata={
                        'pair_type': pair_type,
                        'max_leverage': str(max_leverage),
                        'required_margin': str(required_margin),
                        'available_margin': str(available_margin)
                    }
                )
                
            self._log_leverage_check(order, result, pair_type, required_margin, available_margin)
            return result
            
        except Exception as e:
            logger.error(f"Leverage validation error: {e}")
            return ComplianceResult(
                valid=False,
                violation_type=ComplianceViolationType.LEVERAGE_VIOLATION,
                reason=f"Leverage validation error: {str(e)}"
            )
    
    def calculate_max_position_size(self, instrument: str, price: Decimal, 
                                  available_margin: Decimal) -> int:
        """Calculate maximum position size given leverage limits"""
        pair_type = 'major' if instrument in self.major_pairs else 'minor'
        max_leverage = self.leverage_limits[pair_type]
        
        max_position_value = available_margin * max_leverage
        max_units = int(max_position_value / price)
        
        return max_units
    
    def _log_leverage_check(self, order: OrderRequest, result: ComplianceResult,
                           pair_type: str, required_margin: Decimal, available_margin: Decimal):
        """Log leverage check for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'check_type': 'LEVERAGE_LIMIT',
            'order': {
                'instrument': order.instrument,
                'units': order.units,
                'side': order.side,
                'order_type': order.order_type,
                'account_id': order.account_id
            },
            'leverage_analysis': {
                'pair_type': pair_type,
                'max_leverage': str(self.leverage_limits[pair_type]),
                'required_margin': str(required_margin),
                'available_margin': str(available_margin)
            },
            'result': {
                'valid': result.valid,
                'violation_type': result.violation_type.value if result.violation_type else None,
                'reason': result.reason
            }
        }
        self.audit_log.append(log_entry)
        logger.info(f"Leverage check: {log_entry}")


class USRegulatoryComplianceEngine:
    """Main US regulatory compliance engine"""
    
    def __init__(self):
        self.fifo_engine = FIFOComplianceEngine()
        self.anti_hedging_validator = AntiHedgingValidator(self.fifo_engine)
        self.leverage_validator = LeverageLimitValidator()
        self.audit_log: List[Dict[str, Any]] = []
    
    async def validate_order_compliance(self, order: OrderRequest, 
                                      account_balance: Decimal,
                                      current_margin_used: Decimal = Decimal('0')) -> ComplianceResult:
        """Comprehensive compliance validation"""
        if order.account_region != 'US':
            return ComplianceResult(valid=True)
            
        try:
            # Run all compliance checks
            validations = []
            
            # FIFO compliance
            fifo_result = await self.fifo_engine.validate_order(order)
            validations.append(('FIFO', fifo_result))
            
            if not fifo_result.valid:
                return fifo_result
            
            # Anti-hedging validation
            hedging_result = await self.anti_hedging_validator.validate_no_hedging(order)
            validations.append(('ANTI_HEDGING', hedging_result))
            
            if not hedging_result.valid:
                return hedging_result
            
            # Leverage validation
            leverage_result = await self.leverage_validator.validate_leverage(
                order, account_balance, current_margin_used
            )
            validations.append(('LEVERAGE', leverage_result))
            
            if not leverage_result.valid:
                return leverage_result
            
            # All validations passed
            result = ComplianceResult(
                valid=True,
                metadata={
                    'validations_passed': [v[0] for v in validations],
                    'fifo_metadata': fifo_result.metadata,
                    'leverage_metadata': leverage_result.metadata
                }
            )
            
            self._log_comprehensive_check(order, result, validations)
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive compliance validation error: {e}")
            return ComplianceResult(
                valid=False,
                reason=f"Compliance validation error: {str(e)}"
            )
    
    def get_compliance_summary(self, account_id: str) -> Dict[str, Any]:
        """Get compliance summary for account"""
        return {
            'account_id': account_id,
            'compliance_status': 'ACTIVE',
            'fifo_positions': len(self.fifo_engine.position_queues),
            'total_compliance_checks': len(self.audit_log),
            'recent_violations': [
                log for log in self.audit_log[-50:] 
                if not log.get('result', {}).get('valid', True)
            ]
        }
    
    def _log_comprehensive_check(self, order: OrderRequest, result: ComplianceResult,
                               validations: List[tuple]):
        """Log comprehensive compliance check"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'check_type': 'COMPREHENSIVE_COMPLIANCE',
            'order': {
                'instrument': order.instrument,
                'units': order.units,
                'side': order.side,
                'order_type': order.order_type,
                'account_id': order.account_id
            },
            'validations': [
                {
                    'type': v[0],
                    'valid': v[1].valid,
                    'violation_type': v[1].violation_type.value if v[1].violation_type else None
                }
                for v in validations
            ],
            'result': {
                'valid': result.valid,
                'reason': result.reason
            }
        }
        self.audit_log.append(log_entry)
        logger.info(f"Comprehensive compliance check: {log_entry}")