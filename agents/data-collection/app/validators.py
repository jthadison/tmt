"""
Data validation pipeline for comprehensive trade data collection.

This module implements validators that ensure data quality, detect anomalies,
and prevent corrupted data from entering the learning pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from decimal import Decimal
from datetime import datetime, timedelta
import statistics
import logging

from .data_models import (
    ComprehensiveTradeRecord,
    DataValidationResult,
    ValidationResults,
    ValidationIssue,
    ValidationRecommendations,
    ValidationCategory,
    ValidationSeverity,
)


logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Base class for data validators."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def validate(self, record: ComprehensiveTradeRecord) -> ValidationResults:
        """Validate a trade record."""
        pass
    
    def _create_issue(
        self,
        category: ValidationCategory,
        severity: ValidationSeverity,
        description: str,
        affected_fields: List[str],
        suggested_fix: str = ""
    ) -> ValidationIssue:
        """Create a validation issue."""
        return ValidationIssue(
            category=category,
            severity=severity,
            description=description,
            affected_fields=affected_fields,
            suggested_fix=suggested_fix
        )


class DataCompletenessValidator(BaseValidator):
    """Validates data completeness across all trade record fields."""
    
    CRITICAL_FIELDS = {
        "trade_details.symbol",
        "trade_details.direction",
        "trade_details.size",
        "trade_details.entry_price",
        "signal_context.signal_id",
        "signal_context.confidence",
        "market_conditions.session",
        "market_conditions.market_regime",
    }
    
    REQUIRED_FIELDS = {
        "id",
        "account_id",
        "timestamp",
        "trade_details.symbol",
        "trade_details.direction",
        "trade_details.size",
        "trade_details.entry_price",
        "signal_context.signal_id",
        "signal_context.pattern_type",
    }
    
    def __init__(self):
        super().__init__("DataCompletenessValidator")
    
    def validate(self, record: ComprehensiveTradeRecord) -> ValidationResults:
        """Validate data completeness."""
        issues = []
        
        # Check critical fields
        critical_missing = self._check_critical_fields(record)
        if critical_missing:
            issues.append(self._create_issue(
                ValidationCategory.MISSING_DATA,
                ValidationSeverity.CRITICAL,
                f"Critical fields missing: {', '.join(critical_missing)}",
                critical_missing,
                "Populate missing critical fields before processing"
            ))
        
        # Check required fields
        required_missing = self._check_required_fields(record)
        if required_missing:
            issues.append(self._create_issue(
                ValidationCategory.MISSING_DATA,
                ValidationSeverity.HIGH,
                f"Required fields missing: {', '.join(required_missing)}",
                required_missing,
                "Populate missing required fields for complete analysis"
            ))
        
        # Check optional field completeness
        completeness_score = self._calculate_completeness_score(record)
        
        if completeness_score < Decimal("0.5"):
            issues.append(self._create_issue(
                ValidationCategory.MISSING_DATA,
                ValidationSeverity.MEDIUM,
                f"Low data completeness: {completeness_score:.2f}",
                ["overall_completeness"],
                "Improve data collection to capture more features"
            ))
        
        # Overall validation result
        passed = len([i for i in issues if i.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.HIGH]]) == 0
        
        return ValidationResults(
            passed=passed,
            quality_score=completeness_score,
            completeness_score=completeness_score,
            consistency_score=Decimal("1.0"),  # Not checked by this validator
            anomaly_score=Decimal("0.0")  # Not checked by this validator
        )
    
    def _check_critical_fields(self, record: ComprehensiveTradeRecord) -> List[str]:
        """Check if critical fields are missing."""
        missing = []
        
        for field_path in self.CRITICAL_FIELDS:
            if not self._field_exists_and_valid(record, field_path):
                missing.append(field_path)
        
        return missing
    
    def _check_required_fields(self, record: ComprehensiveTradeRecord) -> List[str]:
        """Check if required fields are missing."""
        missing = []
        
        for field_path in self.REQUIRED_FIELDS:
            if not self._field_exists_and_valid(record, field_path):
                missing.append(field_path)
        
        return missing
    
    def _field_exists_and_valid(self, record: ComprehensiveTradeRecord, field_path: str) -> bool:
        """Check if field exists and has valid value."""
        try:
            parts = field_path.split(".")
            obj = record
            
            for part in parts:
                obj = getattr(obj, part)
                if obj is None or obj == "" or (isinstance(obj, Decimal) and obj == 0):
                    return False
            
            return True
        except AttributeError:
            return False
    
    def _calculate_completeness_score(self, record: ComprehensiveTradeRecord) -> Decimal:
        """Calculate overall data completeness score."""
        total_fields = 0
        filled_fields = 0
        
        # Count fields in main data structures
        for section_name in ["trade_details", "signal_context", "market_conditions", 
                           "execution_quality", "personality_impact", "performance"]:
            section = getattr(record, section_name)
            
            # Count fields in the section
            for field_name, field_value in section.__dict__.items():
                total_fields += 1
                if field_value is not None and field_value != "" and field_value != Decimal("0"):
                    filled_fields += 1
        
        return Decimal(str(filled_fields / total_fields)) if total_fields > 0 else Decimal("0")


class DataConsistencyValidator(BaseValidator):
    """Validates data consistency and logical relationships."""
    
    def __init__(self):
        super().__init__("DataConsistencyValidator")
    
    def validate(self, record: ComprehensiveTradeRecord) -> ValidationResults:
        """Validate data consistency."""
        issues = []
        
        # Validate trade direction consistency
        issues.extend(self._validate_trade_direction_consistency(record))
        
        # Validate price relationships
        issues.extend(self._validate_price_relationships(record))
        
        # Validate time consistency
        issues.extend(self._validate_time_consistency(record))
        
        # Validate performance calculations
        issues.extend(self._validate_performance_consistency(record))
        
        # Calculate consistency score
        critical_issues = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == ValidationSeverity.HIGH])
        
        consistency_score = max(Decimal("0"), Decimal("1.0") - 
                              Decimal(str(critical_issues * 0.5)) - 
                              Decimal(str(high_issues * 0.2)))
        
        passed = critical_issues == 0
        
        return ValidationResults(
            passed=passed,
            quality_score=consistency_score,
            completeness_score=Decimal("1.0"),  # Not checked by this validator
            consistency_score=consistency_score,
            anomaly_score=Decimal("0.0")  # Not checked by this validator
        )
    
    def _validate_trade_direction_consistency(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Validate trade direction is consistent with other fields."""
        issues = []
        
        # Check if PnL direction is consistent with trade direction and price movement
        if (record.trade_details.exit_price and 
            record.trade_details.exit_price > 0 and 
            record.performance.actual_pnl != 0):
            
            price_diff = record.trade_details.exit_price - record.trade_details.entry_price
            expected_pnl_sign = 1 if record.trade_details.direction.value == "long" else -1
            actual_pnl_sign = 1 if record.performance.actual_pnl > 0 else -1
            
            # For long trades: positive price diff should mean positive PnL
            # For short trades: negative price diff should mean positive PnL
            if record.trade_details.direction.value == "long":
                expected_from_price = 1 if price_diff > 0 else -1
            else:
                expected_from_price = 1 if price_diff < 0 else -1
            
            if expected_from_price != actual_pnl_sign:
                issues.append(self._create_issue(
                    ValidationCategory.INCONSISTENT_DATA,
                    ValidationSeverity.HIGH,
                    "Trade direction inconsistent with price movement and PnL",
                    ["trade_details.direction", "performance.actual_pnl"],
                    "Verify trade direction and PnL calculation"
                ))
        
        return issues
    
    def _validate_price_relationships(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Validate price relationships make sense."""
        issues = []
        
        # Check stop loss and take profit are on correct side of entry
        if record.trade_details.direction.value == "long":
            if record.trade_details.stop_loss >= record.trade_details.entry_price:
                issues.append(self._create_issue(
                    ValidationCategory.INCONSISTENT_DATA,
                    ValidationSeverity.HIGH,
                    "Long trade stop loss should be below entry price",
                    ["trade_details.stop_loss", "trade_details.entry_price"],
                    "Verify stop loss placement for long trades"
                ))
            
            if (record.trade_details.take_profit > 0 and 
                record.trade_details.take_profit <= record.trade_details.entry_price):
                issues.append(self._create_issue(
                    ValidationCategory.INCONSISTENT_DATA,
                    ValidationSeverity.HIGH,
                    "Long trade take profit should be above entry price",
                    ["trade_details.take_profit", "trade_details.entry_price"],
                    "Verify take profit placement for long trades"
                ))
        
        elif record.trade_details.direction.value == "short":
            if record.trade_details.stop_loss <= record.trade_details.entry_price:
                issues.append(self._create_issue(
                    ValidationCategory.INCONSISTENT_DATA,
                    ValidationSeverity.HIGH,
                    "Short trade stop loss should be above entry price",
                    ["trade_details.stop_loss", "trade_details.entry_price"],
                    "Verify stop loss placement for short trades"
                ))
        
        return issues
    
    def _validate_time_consistency(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Validate time relationships are logical."""
        issues = []
        
        # Execution time should be after or equal to order placement time
        if (record.execution_quality.fill_time and 
            record.execution_quality.fill_time < record.execution_quality.order_placement_time):
            issues.append(self._create_issue(
                ValidationCategory.TIMING_ISSUES,
                ValidationSeverity.HIGH,
                "Fill time is before order placement time",
                ["execution_quality.fill_time", "execution_quality.order_placement_time"],
                "Verify timestamp accuracy and timezone consistency"
            ))
        
        # Trade timestamp should be reasonable (not too far in future/past)
        now = datetime.now()
        time_diff = abs((record.timestamp - now).total_seconds())
        
        if time_diff > 86400:  # More than 1 day difference
            issues.append(self._create_issue(
                ValidationCategory.TIMING_ISSUES,
                ValidationSeverity.MEDIUM,
                f"Trade timestamp differs from current time by {time_diff/3600:.1f} hours",
                ["timestamp"],
                "Verify timestamp accuracy and timezone settings"
            ))
        
        return issues
    
    def _validate_performance_consistency(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Validate performance calculations are consistent."""
        issues = []
        
        # Performance ratio should match expected/actual PnL relationship
        if (record.performance.expected_pnl != 0 and 
            record.performance.performance_ratio != 0):
            
            calculated_ratio = record.performance.actual_pnl / record.performance.expected_pnl
            ratio_diff = abs(calculated_ratio - record.performance.performance_ratio)
            
            if ratio_diff > Decimal("0.01"):  # More than 1% difference
                issues.append(self._create_issue(
                    ValidationCategory.INCONSISTENT_DATA,
                    ValidationSeverity.MEDIUM,
                    f"Performance ratio inconsistent with PnL values (diff: {ratio_diff:.3f})",
                    ["performance.performance_ratio", "performance.actual_pnl", "performance.expected_pnl"],
                    "Recalculate performance ratio from actual/expected PnL"
                ))
        
        return issues


class AnomalyDetectionValidator(BaseValidator):
    """Detects anomalous values that might indicate data corruption."""
    
    def __init__(self):
        super().__init__("AnomalyDetectionValidator")
        self.historical_stats = {}  # Would be loaded from database in real implementation
    
    def validate(self, record: ComprehensiveTradeRecord) -> ValidationResults:
        """Detect anomalous values in the record."""
        issues = []
        anomaly_score = Decimal("0")
        
        # Check for extreme values
        issues.extend(self._check_extreme_values(record))
        
        # Check for suspicious patterns
        issues.extend(self._check_suspicious_patterns(record))
        
        # Calculate anomaly score based on issues
        critical_anomalies = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        high_anomalies = len([i for i in issues if i.severity == ValidationSeverity.HIGH])
        
        anomaly_score = Decimal(str(critical_anomalies * 0.8 + high_anomalies * 0.4))
        anomaly_score = min(anomaly_score, Decimal("1.0"))  # Cap at 1.0
        
        passed = critical_anomalies == 0
        quality_score = Decimal("1.0") - anomaly_score * Decimal("0.5")
        
        return ValidationResults(
            passed=passed,
            quality_score=quality_score,
            completeness_score=Decimal("1.0"),  # Not checked by this validator
            consistency_score=Decimal("1.0"),  # Not checked by this validator
            anomaly_score=anomaly_score
        )
    
    def _check_extreme_values(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Check for extreme/impossible values."""
        issues = []
        
        # Check for negative prices
        if record.trade_details.entry_price <= 0:
            issues.append(self._create_issue(
                ValidationCategory.ANOMALOUS_VALUES,
                ValidationSeverity.CRITICAL,
                f"Entry price is non-positive: {record.trade_details.entry_price}",
                ["trade_details.entry_price"],
                "Verify price data source and calculation"
            ))
        
        # Check for extreme position sizes
        if record.trade_details.size <= 0 or record.trade_details.size > Decimal("100000"):
            issues.append(self._create_issue(
                ValidationCategory.ANOMALOUS_VALUES,
                ValidationSeverity.HIGH,
                f"Unusual position size: {record.trade_details.size}",
                ["trade_details.size"],
                "Verify position sizing calculation"
            ))
        
        # Check for extreme execution latency
        if record.execution_quality.execution_latency > 60000:  # More than 1 minute
            issues.append(self._create_issue(
                ValidationCategory.ANOMALOUS_VALUES,
                ValidationSeverity.HIGH,
                f"Extreme execution latency: {record.execution_quality.execution_latency}ms",
                ["execution_quality.execution_latency"],
                "Investigate execution system performance"
            ))
        
        # Check for extreme slippage
        if abs(record.execution_quality.slippage) > 50:  # More than 50 pips
            issues.append(self._create_issue(
                ValidationCategory.ANOMALOUS_VALUES,
                ValidationSeverity.MEDIUM,
                f"High slippage detected: {record.execution_quality.slippage} pips",
                ["execution_quality.slippage"],
                "Review execution quality and market conditions"
            ))
        
        return issues
    
    def _check_suspicious_patterns(self, record: ComprehensiveTradeRecord) -> List[ValidationIssue]:
        """Check for suspicious data patterns."""
        issues = []
        
        # Check for too many perfect/round numbers
        round_numbers = 0
        total_decimal_fields = 0
        
        for section_name in ["trade_details", "market_conditions", "execution_quality", "performance"]:
            section = getattr(record, section_name)
            for field_name, field_value in section.__dict__.items():
                if isinstance(field_value, Decimal):
                    total_decimal_fields += 1
                    if field_value == field_value.quantize(Decimal("1")):  # Round number
                        round_numbers += 1
        
        if total_decimal_fields > 0:
            round_percentage = round_numbers / total_decimal_fields
            if round_percentage > 0.8:  # More than 80% round numbers
                issues.append(self._create_issue(
                    ValidationCategory.ANOMALOUS_VALUES,
                    ValidationSeverity.MEDIUM,
                    f"Suspiciously high percentage of round numbers: {round_percentage:.1%}",
                    ["data_quality"],
                    "Review data collection precision and sources"
                ))
        
        return issues


class TimingValidationValidator(BaseValidator):
    """Validates timing-related aspects of trade data."""
    
    def __init__(self):
        super().__init__("TimingValidationValidator")
    
    def validate(self, record: ComprehensiveTradeRecord) -> ValidationResults:
        """Validate timing aspects of the record."""
        issues = []
        
        # Check timestamp is in reasonable range
        now = datetime.now()
        future_threshold = now + timedelta(hours=1)
        past_threshold = now - timedelta(days=30)
        
        if record.timestamp > future_threshold:
            issues.append(self._create_issue(
                ValidationCategory.TIMING_ISSUES,
                ValidationSeverity.HIGH,
                "Trade timestamp is in the future",
                ["timestamp"],
                "Verify system clock synchronization"
            ))
        
        if record.timestamp < past_threshold:
            issues.append(self._create_issue(
                ValidationCategory.TIMING_ISSUES,
                ValidationSeverity.MEDIUM,
                "Trade timestamp is more than 30 days old",
                ["timestamp"],
                "Verify data is not stale or from incorrect time period"
            ))
        
        # Validate execution timing relationships
        if (record.execution_quality.fill_time and 
            record.execution_quality.order_placement_time):
            
            time_diff = (record.execution_quality.fill_time - 
                        record.execution_quality.order_placement_time).total_seconds() * 1000
            
            if time_diff != record.execution_quality.execution_latency:
                issues.append(self._create_issue(
                    ValidationCategory.TIMING_ISSUES,
                    ValidationSeverity.LOW,
                    "Calculated execution latency doesn't match recorded latency",
                    ["execution_quality.execution_latency"],
                    "Recalculate latency from timestamps"
                ))
        
        # Check market session consistency with timestamp
        expected_session = self._determine_expected_session(record.timestamp)
        if record.market_conditions.session != expected_session:
            issues.append(self._create_issue(
                ValidationCategory.TIMING_ISSUES,
                ValidationSeverity.LOW,
                f"Market session {record.market_conditions.session} inconsistent with timestamp",
                ["market_conditions.session"],
                "Verify session determination logic"
            ))
        
        # Overall validation result
        critical_issues = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        passed = critical_issues == 0
        
        quality_score = Decimal("1.0") - Decimal(str(len(issues) * 0.1))
        quality_score = max(quality_score, Decimal("0"))
        
        return ValidationResults(
            passed=passed,
            quality_score=quality_score,
            completeness_score=Decimal("1.0"),  # Not checked by this validator
            consistency_score=Decimal("1.0"),  # Not checked by this validator
            anomaly_score=Decimal("0.0")  # Not checked by this validator
        )
    
    def _determine_expected_session(self, timestamp: datetime) -> str:
        """Determine expected market session from timestamp."""
        hour = timestamp.hour
        
        if 0 <= hour < 7:
            return "asian"
        elif 7 <= hour < 12:
            return "overlap" if hour <= 9 else "london"
        elif 12 <= hour < 17:
            return "overlap" if hour <= 15 else "newyork"
        else:
            return "newyork"