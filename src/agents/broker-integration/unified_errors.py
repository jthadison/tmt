"""
Unified Error Handling System
Story 8.10 - Task 4: Create unified error handling (AC4)
"""
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class StandardErrorCode(Enum):
    """Standardized error codes across all brokers"""
    
    # Authentication Errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Account Errors
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    MARGIN_CALL = "MARGIN_CALL"
    
    # Order Errors
    INVALID_ORDER = "INVALID_ORDER"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_PRICE = "INVALID_PRICE"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_ALREADY_FILLED = "ORDER_ALREADY_FILLED"
    ORDER_ALREADY_CANCELLED = "ORDER_ALREADY_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    
    # Market Errors
    MARKET_CLOSED = "MARKET_CLOSED"
    TRADING_HALTED = "TRADING_HALTED"
    INSTRUMENT_NOT_TRADEABLE = "INSTRUMENT_NOT_TRADEABLE"
    PRICE_OUT_OF_RANGE = "PRICE_OUT_OF_RANGE"
    
    # Position Errors
    POSITION_NOT_FOUND = "POSITION_NOT_FOUND"
    CANNOT_CLOSE_POSITION = "CANNOT_CLOSE_POSITION"
    HEDGING_NOT_ALLOWED = "HEDGING_NOT_ALLOWED"
    FIFO_VIOLATION = "FIFO_VIOLATION"
    
    # Technical Errors
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT = "TIMEOUT"
    SERVER_ERROR = "SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATA_ERROR = "DATA_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Regulatory Errors
    REGULATORY_RESTRICTION = "REGULATORY_RESTRICTION"
    PDT_VIOLATION = "PDT_VIOLATION"  # Pattern Day Trader
    WASH_SALE_RULE = "WASH_SALE_RULE"
    
    # Unknown/Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    TECHNICAL = "technical"
    REGULATORY = "regulatory"
    MARKET_DATA = "market_data"
    CONNECTIVITY = "connectivity"


@dataclass
class ErrorContext:
    """Additional context for errors"""
    broker_name: str
    account_id: Optional[str] = None
    order_id: Optional[str] = None
    instrument: Optional[str] = None
    operation: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorDetails:
    """Detailed error information"""
    error_code: StandardErrorCode
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    broker_specific_code: Optional[str] = None
    broker_specific_message: Optional[str] = None
    context: Optional[ErrorContext] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_retryable: bool = False
    retry_after_seconds: Optional[int] = None
    suggested_action: Optional[str] = None
    documentation_url: Optional[str] = None


class StandardBrokerError(Exception):
    """Standardized broker error with unified error codes"""
    
    def __init__(self, 
                 error_code: StandardErrorCode,
                 message: str,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: Optional[ErrorCategory] = None,
                 broker_specific_code: Optional[str] = None,
                 broker_specific_message: Optional[str] = None,
                 context: Optional[ErrorContext] = None,
                 is_retryable: bool = False,
                 retry_after_seconds: Optional[int] = None,
                 suggested_action: Optional[str] = None):
        
        self.error_code = error_code
        self.message = message
        self.severity = severity
        self.category = category or self._infer_category(error_code)
        self.broker_specific_code = broker_specific_code
        self.broker_specific_message = broker_specific_message
        self.context = context
        self.timestamp = datetime.now(timezone.utc)
        self.is_retryable = is_retryable
        self.retry_after_seconds = retry_after_seconds
        self.suggested_action = suggested_action
        
        super().__init__(f"{error_code.value}: {message}")
        
    def _infer_category(self, error_code: StandardErrorCode) -> ErrorCategory:
        """Infer error category from error code"""
        auth_codes = {
            StandardErrorCode.AUTHENTICATION_FAILED,
            StandardErrorCode.INVALID_CREDENTIALS,
            StandardErrorCode.SESSION_EXPIRED
        }
        
        authz_codes = {
            StandardErrorCode.ACCESS_DENIED,
            StandardErrorCode.RATE_LIMITED
        }
        
        validation_codes = {
            StandardErrorCode.INVALID_ORDER,
            StandardErrorCode.INVALID_SYMBOL,
            StandardErrorCode.INVALID_QUANTITY,
            StandardErrorCode.INVALID_PRICE,
            StandardErrorCode.VALIDATION_ERROR
        }
        
        business_codes = {
            StandardErrorCode.INSUFFICIENT_FUNDS,
            StandardErrorCode.INSUFFICIENT_MARGIN,
            StandardErrorCode.ORDER_REJECTED,
            StandardErrorCode.CANNOT_CLOSE_POSITION
        }
        
        technical_codes = {
            StandardErrorCode.CONNECTION_ERROR,
            StandardErrorCode.TIMEOUT,
            StandardErrorCode.SERVER_ERROR,
            StandardErrorCode.SERVICE_UNAVAILABLE,
            StandardErrorCode.DATA_ERROR
        }
        
        regulatory_codes = {
            StandardErrorCode.REGULATORY_RESTRICTION,
            StandardErrorCode.PDT_VIOLATION,
            StandardErrorCode.WASH_SALE_RULE,
            StandardErrorCode.FIFO_VIOLATION,
            StandardErrorCode.HEDGING_NOT_ALLOWED
        }
        
        market_codes = {
            StandardErrorCode.MARKET_CLOSED,
            StandardErrorCode.TRADING_HALTED,
            StandardErrorCode.INSTRUMENT_NOT_TRADEABLE,
            StandardErrorCode.PRICE_OUT_OF_RANGE
        }
        
        if error_code in auth_codes:
            return ErrorCategory.AUTHENTICATION
        elif error_code in authz_codes:
            return ErrorCategory.AUTHORIZATION
        elif error_code in validation_codes:
            return ErrorCategory.VALIDATION
        elif error_code in business_codes:
            return ErrorCategory.BUSINESS_LOGIC
        elif error_code in technical_codes:
            return ErrorCategory.TECHNICAL
        elif error_code in regulatory_codes:
            return ErrorCategory.REGULATORY
        elif error_code in market_codes:
            return ErrorCategory.MARKET_DATA
        else:
            return ErrorCategory.TECHNICAL
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation"""
        return {
            'error_code': self.error_code.value,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category.value,
            'broker_specific_code': self.broker_specific_code,
            'broker_specific_message': self.broker_specific_message,
            'timestamp': self.timestamp.isoformat(),
            'is_retryable': self.is_retryable,
            'retry_after_seconds': self.retry_after_seconds,
            'suggested_action': self.suggested_action,
            'context': self.context.__dict__ if self.context else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardBrokerError':
        """Create error from dictionary representation"""
        context = None
        if data.get('context'):
            context = ErrorContext(**data['context'])
            
        return cls(
            error_code=StandardErrorCode(data['error_code']),
            message=data['message'],
            severity=ErrorSeverity(data['severity']),
            category=ErrorCategory(data['category']) if data.get('category') else None,
            broker_specific_code=data.get('broker_specific_code'),
            broker_specific_message=data.get('broker_specific_message'),
            context=context,
            is_retryable=data.get('is_retryable', False),
            retry_after_seconds=data.get('retry_after_seconds'),
            suggested_action=data.get('suggested_action')
        )


class ErrorCodeMapper:
    """Maps broker-specific errors to standard codes"""
    
    def __init__(self):
        self.mappings: Dict[str, Dict[str, Dict[str, Any]]] = {
            'oanda': {
                # Authentication errors
                'UNAUTHORIZED': {
                    'code': StandardErrorCode.AUTHENTICATION_FAILED,
                    'severity': ErrorSeverity.HIGH,
                    'retryable': False,
                    'action': 'Check API credentials'
                },
                'FORBIDDEN': {
                    'code': StandardErrorCode.ACCESS_DENIED,
                    'severity': ErrorSeverity.HIGH,
                    'retryable': False,
                    'action': 'Check account permissions'
                },
                
                # Account errors
                'INSUFFICIENT_MARGIN': {
                    'code': StandardErrorCode.INSUFFICIENT_MARGIN,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Increase account balance or reduce position size'
                },
                'ACCOUNT_NOT_TRADABLE': {
                    'code': StandardErrorCode.ACCOUNT_DISABLED,
                    'severity': ErrorSeverity.HIGH,
                    'retryable': False,
                    'action': 'Contact broker support'
                },
                
                # Order errors
                'INVALID_INSTRUMENT': {
                    'code': StandardErrorCode.INVALID_SYMBOL,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Use valid trading instrument'
                },
                'INVALID_UNITS': {
                    'code': StandardErrorCode.INVALID_QUANTITY,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Check minimum/maximum trade size'
                },
                'ORDER_DOESNT_EXIST': {
                    'code': StandardErrorCode.ORDER_NOT_FOUND,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Verify order ID'
                },
                
                # Market errors
                'MARKET_CLOSED': {
                    'code': StandardErrorCode.MARKET_CLOSED,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': True,
                    'retry_after': 3600,
                    'action': 'Wait for market to open'
                },
                'INSTRUMENT_NOT_TRADEABLE': {
                    'code': StandardErrorCode.INSTRUMENT_NOT_TRADEABLE,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Choose different instrument'
                },
                
                # Technical errors
                'TIMEOUT': {
                    'code': StandardErrorCode.TIMEOUT,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': True,
                    'retry_after': 30,
                    'action': 'Retry request'
                },
                'SERVER_ERROR': {
                    'code': StandardErrorCode.SERVER_ERROR,
                    'severity': ErrorSeverity.HIGH,
                    'retryable': True,
                    'retry_after': 60,
                    'action': 'Retry after delay'
                }
            },
            
            # Add mappings for other brokers
            'interactive_brokers': {
                # IB-specific error mappings
                '2104': {  # Market data farm connection is OK
                    'code': StandardErrorCode.CONNECTION_ERROR,
                    'severity': ErrorSeverity.LOW,
                    'retryable': True,
                    'action': 'Connection restored'
                },
                '2106': {  # HMDS data farm connection is OK
                    'code': StandardErrorCode.CONNECTION_ERROR,
                    'severity': ErrorSeverity.LOW,
                    'retryable': True,
                    'action': 'Historical data connection restored'
                },
                '200': {  # No security definition found
                    'code': StandardErrorCode.INVALID_SYMBOL,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Check symbol format'
                }
            },
            
            'alpaca': {
                # Alpaca-specific error mappings
                '40010001': {  # Insufficient buying power
                    'code': StandardErrorCode.INSUFFICIENT_FUNDS,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Reduce order size or add funds'
                },
                '40310000': {  # Order not found
                    'code': StandardErrorCode.ORDER_NOT_FOUND,
                    'severity': ErrorSeverity.MEDIUM,
                    'retryable': False,
                    'action': 'Verify order ID'
                }
            }
        }
        
    def map_error(self, 
                  broker_name: str, 
                  broker_error_code: str, 
                  message: str,
                  context: Optional[ErrorContext] = None) -> StandardBrokerError:
        """
        Map broker error to standard error
        
        Args:
            broker_name: Name of the broker
            broker_error_code: Broker-specific error code
            message: Error message
            context: Optional error context
            
        Returns:
            StandardBrokerError with unified error code
        """
        broker_mappings = self.mappings.get(broker_name.lower(), {})
        error_mapping = broker_mappings.get(broker_error_code, {})
        
        standard_code = error_mapping.get('code', StandardErrorCode.UNKNOWN_ERROR)
        severity = error_mapping.get('severity', ErrorSeverity.MEDIUM)
        is_retryable = error_mapping.get('retryable', False)
        retry_after = error_mapping.get('retry_after')
        suggested_action = error_mapping.get('action')
        
        return StandardBrokerError(
            error_code=standard_code,
            message=message,
            severity=severity,
            broker_specific_code=broker_error_code,
            broker_specific_message=message,
            context=context,
            is_retryable=is_retryable,
            retry_after_seconds=retry_after,
            suggested_action=suggested_action
        )
        
    def add_mapping(self, 
                   broker_name: str,
                   broker_error_code: str,
                   standard_error_code: StandardErrorCode,
                   severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                   is_retryable: bool = False,
                   retry_after_seconds: Optional[int] = None,
                   suggested_action: Optional[str] = None):
        """Add custom error mapping"""
        if broker_name not in self.mappings:
            self.mappings[broker_name] = {}
            
        self.mappings[broker_name][broker_error_code] = {
            'code': standard_error_code,
            'severity': severity,
            'retryable': is_retryable,
            'retry_after': retry_after_seconds,
            'action': suggested_action
        }
        
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error mapping statistics"""
        total_mappings = sum(len(broker_mappings) for broker_mappings in self.mappings.values())
        
        return {
            'total_brokers': len(self.mappings),
            'total_mappings': total_mappings,
            'brokers': list(self.mappings.keys()),
            'mappings_per_broker': {
                broker: len(mappings) for broker, mappings in self.mappings.items()
            }
        }


class ErrorAggregator:
    """Aggregates and analyzes error patterns"""
    
    def __init__(self):
        self.error_history: List[StandardBrokerError] = []
        self.max_history_size = 10000
        
    def record_error(self, error: StandardBrokerError):
        """Record error for analysis"""
        self.error_history.append(error)
        
        # Keep history size bounded
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
            
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time window"""
        cutoff = datetime.now(timezone.utc) - datetime.timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff]
        
        if not recent_errors:
            return {'total_errors': 0}
            
        # Count by error code
        error_counts = {}
        severity_counts = {}
        category_counts = {}
        broker_counts = {}
        
        for error in recent_errors:
            error_counts[error.error_code.value] = error_counts.get(error.error_code.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            
            if error.context and error.context.broker_name:
                broker = error.context.broker_name
                broker_counts[broker] = broker_counts.get(broker, 0) + 1
                
        return {
            'total_errors': len(recent_errors),
            'time_window_hours': hours,
            'error_counts': error_counts,
            'severity_counts': severity_counts,
            'category_counts': category_counts,
            'broker_counts': broker_counts,
            'most_common_error': max(error_counts.items(), key=lambda x: x[1]) if error_counts else None,
            'error_rate_per_hour': len(recent_errors) / hours
        }
        
    def get_broker_error_comparison(self) -> Dict[str, Dict[str, Any]]:
        """Compare error rates across brokers"""
        broker_stats = {}
        
        for error in self.error_history:
            if not error.context or not error.context.broker_name:
                continue
                
            broker = error.context.broker_name
            if broker not in broker_stats:
                broker_stats[broker] = {
                    'total_errors': 0,
                    'error_codes': {},
                    'severity_counts': {},
                    'last_error': None
                }
                
            stats = broker_stats[broker]
            stats['total_errors'] += 1
            stats['error_codes'][error.error_code.value] = stats['error_codes'].get(error.error_code.value, 0) + 1
            stats['severity_counts'][error.severity.value] = stats['severity_counts'].get(error.severity.value, 0) + 1
            
            if not stats['last_error'] or error.timestamp > stats['last_error']:
                stats['last_error'] = error.timestamp
                
        return broker_stats


# Global instances
error_mapper = ErrorCodeMapper()
error_aggregator = ErrorAggregator()


def create_standard_error(error_code: StandardErrorCode,
                         message: str,
                         broker_name: Optional[str] = None,
                         broker_error_code: Optional[str] = None,
                         context: Optional[ErrorContext] = None,
                         **kwargs) -> StandardBrokerError:
    """Convenience function to create standard broker error"""
    return StandardBrokerError(
        error_code=error_code,
        message=message,
        broker_specific_code=broker_error_code,
        context=context or (ErrorContext(broker_name=broker_name) if broker_name else None),
        **kwargs
    )


def map_broker_error(broker_name: str,
                    broker_error_code: str,
                    message: str,
                    context: Optional[ErrorContext] = None) -> StandardBrokerError:
    """Convenience function to map broker error"""
    error = error_mapper.map_error(broker_name, broker_error_code, message, context)
    error_aggregator.record_error(error)
    return error