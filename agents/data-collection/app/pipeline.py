"""
Main data collection pipeline.

This module orchestrates the complete data collection process including
feature extraction, validation, pattern tracking, and storage.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import logging
import asyncio
from dataclasses import dataclass

from .data_models import (
    ComprehensiveTradeRecord,
    TradeEvent,
    DataValidationResult,
    ValidationRecommendations,
    TradeDetails,
    SignalContext,
    MarketConditions,
    ExecutionQuality,
    PersonalityImpact,
    Performance,
    LearningMetadata,
    TradeDirection,
    TradeStatus,
)
from .feature_extractors import (
    MarketConditionExtractor,
    SignalContextExtractor,
    ExecutionQualityExtractor,
    PersonalityImpactExtractor,
    PerformanceCalculator,
    LearningMetadataExtractor,
)
from .validators import (
    DataCompletenessValidator,
    DataConsistencyValidator,
    AnomalyDetectionValidator,
    TimingValidationValidator,
)
from .pattern_tracker import PatternPerformanceAnalyzer
from .execution_analyzer import ExecutionQualityReporter
from .false_signal_analyzer import RejectedSignalAnalyzer


logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the data collection pipeline."""
    validate_data: bool = True
    store_invalid_data: bool = True
    quarantine_threshold: Decimal = Decimal("0.5")  # Quality score threshold
    learning_threshold: Decimal = Decimal("0.8")  # Threshold for learning eligibility
    enable_pattern_tracking: bool = True
    enable_execution_analysis: bool = True
    enable_false_signal_analysis: bool = True


@dataclass
class PipelineMetrics:
    """Metrics for pipeline performance monitoring."""
    total_records_processed: int = 0
    valid_records: int = 0
    quarantined_records: int = 0
    learning_eligible_records: int = 0
    processing_errors: int = 0
    average_processing_time_ms: Decimal = Decimal("0")
    last_processed_timestamp: Optional[datetime] = None


class DataSanitizer:
    """Sanitizes data before processing."""
    
    def sanitize_trade_event(self, trade_event: TradeEvent) -> TradeEvent:
        """Sanitize trade event data."""
        
        # Clean string fields
        sanitized_event = trade_event
        
        # Remove potentially harmful characters from string fields
        if sanitized_event.event_data:
            sanitized_event.event_data = self._sanitize_dict(sanitized_event.event_data)
        
        if sanitized_event.market_data:
            sanitized_event.market_data = self._sanitize_dict(sanitized_event.market_data)
        
        if sanitized_event.signal_data:
            sanitized_event.signal_data = self._sanitize_dict(sanitized_event.signal_data)
        
        if sanitized_event.execution_data:
            sanitized_event.execution_data = self._sanitize_dict(sanitized_event.execution_data)
        
        return sanitized_event
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data."""
        sanitized = {}
        
        for key, value in data.items():
            # Remove potentially harmful characters from keys
            clean_key = self._sanitize_string(key)
            
            # Sanitize values
            if isinstance(value, str):
                sanitized[clean_key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    self._sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value
        
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string data."""
        if not isinstance(text, str):
            return str(text)
        
        # Remove null bytes and other control characters
        sanitized = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # Limit length to prevent oversized data
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000] + "..."
            logger.warning(f"Truncated oversized string data: {len(text)} -> 1000 chars")
        
        return sanitized.strip()


class DataQualityScorer:
    """Scores overall data quality."""
    
    def calculate_overall_quality_score(
        self,
        validation_result: DataValidationResult,
        feature_completeness: Decimal
    ) -> Decimal:
        """Calculate overall data quality score."""
        
        # Weight different quality aspects
        completeness_weight = Decimal("0.3")
        consistency_weight = Decimal("0.3")
        anomaly_weight = Decimal("0.2")
        validation_weight = Decimal("0.2")
        
        # Calculate weighted score
        quality_score = (
            validation_result.validation.completeness_score * completeness_weight +
            validation_result.validation.consistency_score * consistency_weight +
            (Decimal("1") - validation_result.validation.anomaly_score) * anomaly_weight +
            (Decimal("1") if validation_result.validation.passed else Decimal("0")) * validation_weight
        )
        
        # Adjust for feature completeness
        quality_score *= feature_completeness
        
        return min(quality_score, Decimal("1.0"))


class DataValidationReporter:
    """Generates data validation reports."""
    
    def generate_validation_report(
        self,
        validation_results: List[DataValidationResult],
        timeframe_start: datetime,
        timeframe_end: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        
        if not validation_results:
            return self._create_empty_report(timeframe_start, timeframe_end)
        
        # Calculate summary statistics
        total_records = len(validation_results)
        passed_records = len([r for r in validation_results if r.validation.passed])
        failed_records = total_records - passed_records
        
        # Calculate average quality scores
        avg_quality = sum(r.validation.quality_score for r in validation_results) / total_records
        avg_completeness = sum(r.validation.completeness_score for r in validation_results) / total_records
        avg_consistency = sum(r.validation.consistency_score for r in validation_results) / total_records
        avg_anomaly = sum(r.validation.anomaly_score for r in validation_results) / total_records
        
        # Analyze common issues
        common_issues = self._analyze_common_issues(validation_results)
        
        # Generate recommendations
        recommendations = self._generate_validation_recommendations(validation_results)
        
        return {
            "timeframe": {
                "start": timeframe_start.isoformat(),
                "end": timeframe_end.isoformat()
            },
            "summary": {
                "total_records": total_records,
                "passed_records": passed_records,
                "failed_records": failed_records,
                "pass_rate": float(passed_records / total_records),
                "average_quality_score": float(avg_quality),
                "average_completeness_score": float(avg_completeness),
                "average_consistency_score": float(avg_consistency),
                "average_anomaly_score": float(avg_anomaly)
            },
            "common_issues": common_issues,
            "recommendations": recommendations
        }
    
    def _analyze_common_issues(
        self,
        validation_results: List[DataValidationResult]
    ) -> List[Dict[str, Any]]:
        """Analyze common validation issues."""
        
        issue_counts = {}
        
        for result in validation_results:
            for issue in result.issues:
                key = f"{issue.category.value}_{issue.severity.value}"
                if key not in issue_counts:
                    issue_counts[key] = {
                        "category": issue.category.value,
                        "severity": issue.severity.value,
                        "count": 0,
                        "examples": []
                    }
                
                issue_counts[key]["count"] += 1
                if len(issue_counts[key]["examples"]) < 3:
                    issue_counts[key]["examples"].append(issue.description)
        
        # Sort by count and return top issues
        sorted_issues = sorted(issue_counts.values(), key=lambda x: x["count"], reverse=True)
        return sorted_issues[:10]  # Top 10 issues
    
    def _generate_validation_recommendations(
        self,
        validation_results: List[DataValidationResult]
    ) -> List[str]:
        """Generate validation improvement recommendations."""
        
        recommendations = []
        
        # Analyze failure patterns
        failed_results = [r for r in validation_results if not r.validation.passed]
        
        if len(failed_results) > len(validation_results) * 0.1:  # > 10% failure rate
            recommendations.append("High validation failure rate detected - review data collection processes")
        
        # Check completeness issues
        low_completeness = [r for r in validation_results if r.validation.completeness_score < Decimal("0.7")]
        if len(low_completeness) > len(validation_results) * 0.2:  # > 20% low completeness
            recommendations.append("Significant data completeness issues - improve feature extraction")
        
        # Check consistency issues
        low_consistency = [r for r in validation_results if r.validation.consistency_score < Decimal("0.8")]
        if len(low_consistency) > len(validation_results) * 0.1:  # > 10% low consistency
            recommendations.append("Data consistency issues detected - review data relationships")
        
        # Check anomaly issues
        high_anomaly = [r for r in validation_results if r.validation.anomaly_score > Decimal("0.3")]
        if len(high_anomaly) > len(validation_results) * 0.05:  # > 5% high anomaly
            recommendations.append("Anomalous data detected - investigate data sources")
        
        if not recommendations:
            recommendations.append("Data validation quality is generally good")
        
        return recommendations
    
    def _create_empty_report(
        self,
        timeframe_start: datetime,
        timeframe_end: datetime
    ) -> Dict[str, Any]:
        """Create empty validation report."""
        return {
            "timeframe": {
                "start": timeframe_start.isoformat(),
                "end": timeframe_end.isoformat()
            },
            "summary": {
                "total_records": 0,
                "passed_records": 0,
                "failed_records": 0,
                "pass_rate": 0.0,
                "average_quality_score": 0.0
            },
            "common_issues": [],
            "recommendations": ["No data to analyze"]
        }


class DataCollectionPipeline:
    """Main data collection pipeline orchestrator."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.metrics = PipelineMetrics()
        
        # Initialize components
        self.sanitizer = DataSanitizer()
        self.quality_scorer = DataQualityScorer()
        self.validation_reporter = DataValidationReporter()
        
        # Initialize feature extractors
        self.feature_extractors = [
            MarketConditionExtractor(),
            SignalContextExtractor(),
            ExecutionQualityExtractor(),
            PersonalityImpactExtractor(),
            PerformanceCalculator(),
            LearningMetadataExtractor(),
        ]
        
        # Initialize validators
        self.validators = [
            DataCompletenessValidator(),
            DataConsistencyValidator(),
            AnomalyDetectionValidator(),
            TimingValidationValidator(),
        ]
        
        # Initialize analyzers
        if self.config.enable_pattern_tracking:
            self.pattern_analyzer = PatternPerformanceAnalyzer()
        
        if self.config.enable_execution_analysis:
            self.execution_analyzer = ExecutionQualityReporter()
        
        if self.config.enable_false_signal_analysis:
            self.false_signal_analyzer = RejectedSignalAnalyzer()
        
        # Storage components (would be implemented with actual database connections)
        self.storage_manager = None  # Would be DataStorageManager()
        
        logger.info("Data collection pipeline initialized")
    
    async def process_trade_event(self, trade_event: TradeEvent) -> Optional[ComprehensiveTradeRecord]:
        """Process a single trade event through the complete pipeline."""
        
        start_time = datetime.now()
        
        try:
            # Step 1: Sanitize data
            sanitized_event = self.sanitizer.sanitize_trade_event(trade_event)
            
            # Step 2: Extract features
            record = await self._extract_features(sanitized_event)
            
            # Step 3: Validate data (if enabled)
            if self.config.validate_data:
                validation_result = await self._validate_record(record)
                record.learning_metadata.validation_errors = [
                    issue.description for issue in validation_result.issues
                ]
            else:
                validation_result = None
            
            # Step 4: Score data quality
            if validation_result:
                quality_score = self.quality_scorer.calculate_overall_quality_score(
                    validation_result, record.learning_metadata.feature_completeness
                )
                record.learning_metadata.data_quality = quality_score
                
                # Determine learning eligibility
                record.learning_metadata.learning_eligible = (
                    quality_score >= self.config.learning_threshold and
                    validation_result.validation.passed
                )
            
            # Step 5: Store record (with quarantine if needed)
            stored = await self._store_record(record, validation_result)
            
            # Step 6: Update metrics
            self._update_metrics(start_time, record, validation_result)
            
            if stored:
                logger.debug(f"Successfully processed trade record: {record.id}")
                return record
            else:
                logger.warning(f"Failed to store trade record: {record.id}")
                return None
                
        except Exception as e:
            self.metrics.processing_errors += 1
            logger.error(f"Error processing trade event {trade_event.trade_id}: {str(e)}")
            return None
    
    async def _extract_features(self, trade_event: TradeEvent) -> ComprehensiveTradeRecord:
        """Extract all features from trade event."""
        
        # Extract features from each extractor
        extracted_features = {}
        for extractor in self.feature_extractors:
            try:
                features = extractor.extract(trade_event)
                extracted_features.update(features)
            except Exception as e:
                logger.error(f"Feature extraction error with {extractor.__class__.__name__}: {str(e)}")
        
        # Build comprehensive trade record
        record = self._build_trade_record(trade_event, extracted_features)
        
        return record
    
    def _build_trade_record(
        self,
        trade_event: TradeEvent,
        features: Dict[str, Any]
    ) -> ComprehensiveTradeRecord:
        """Build comprehensive trade record from extracted features."""
        
        # Extract trade details
        trade_data = trade_event.event_data.get("trade", {})
        
        trade_details = TradeDetails(
            symbol=features.get("symbol", trade_data.get("symbol", "")),
            direction=TradeDirection(trade_data.get("direction", "long")),
            size=Decimal(str(trade_data.get("size", 0))),
            entry_price=Decimal(str(trade_data.get("entry_price", 0))),
            exit_price=Decimal(str(trade_data.get("exit_price", 0))) if trade_data.get("exit_price") else None,
            stop_loss=Decimal(str(trade_data.get("stop_loss", 0))),
            take_profit=Decimal(str(trade_data.get("take_profit", 0))),
            status=TradeStatus(trade_data.get("status", "open")),
        )
        
        # Build other sections using extracted features
        signal_context = SignalContext(**{k: v for k, v in features.items() if k in SignalContext.__annotations__})
        market_conditions = MarketConditions(**{k: v for k, v in features.items() if k in MarketConditions.__annotations__})
        execution_quality = ExecutionQuality(**{k: v for k, v in features.items() if k in ExecutionQuality.__annotations__})
        personality_impact = PersonalityImpact(**{k: v for k, v in features.items() if k in PersonalityImpact.__annotations__})
        performance = Performance(**{k: v for k, v in features.items() if k in Performance.__annotations__})
        learning_metadata = LearningMetadata(**{k: v for k, v in features.items() if k in LearningMetadata.__annotations__})
        
        return ComprehensiveTradeRecord(
            id=trade_event.trade_id,
            account_id=trade_event.account_id,
            timestamp=trade_event.timestamp,
            trade_details=trade_details,
            signal_context=signal_context,
            market_conditions=market_conditions,
            execution_quality=execution_quality,
            personality_impact=personality_impact,
            performance=performance,
            learning_metadata=learning_metadata
        )
    
    async def _validate_record(self, record: ComprehensiveTradeRecord) -> DataValidationResult:
        """Validate trade record using all validators."""
        
        validation_result = DataValidationResult(
            record_id=record.id,
            timestamp=datetime.now(),
            validation=None,
            issues=[]
        )
        
        # Run all validators
        validation_results = []
        all_issues = []
        
        for validator in self.validators:
            try:
                result = validator.validate(record)
                validation_results.append(result)
                # Issues would be extracted from validator-specific results
            except Exception as e:
                logger.error(f"Validation error with {validator.name}: {str(e)}")
        
        # Combine validation results
        if validation_results:
            overall_passed = all(r.passed for r in validation_results)
            avg_quality = sum(r.quality_score for r in validation_results) / len(validation_results)
            avg_completeness = sum(r.completeness_score for r in validation_results) / len(validation_results)
            avg_consistency = sum(r.consistency_score for r in validation_results) / len(validation_results)
            avg_anomaly = sum(r.anomaly_score for r in validation_results) / len(validation_results)
            
            from .data_models import ValidationResults
            validation_result.validation = ValidationResults(
                passed=overall_passed,
                quality_score=avg_quality,
                completeness_score=avg_completeness,
                consistency_score=avg_consistency,
                anomaly_score=avg_anomaly
            )
        
        # Generate recommendations
        if validation_result.validation and not validation_result.validation.passed:
            validation_result.recommendations = ValidationRecommendations(
                use_for_learning=validation_result.validation.quality_score >= self.config.learning_threshold,
                quarantine=validation_result.validation.quality_score < self.config.quarantine_threshold,
                requires_review=validation_result.validation.anomaly_score > Decimal("0.5"),
                confidence_reduction=validation_result.validation.anomaly_score * Decimal("0.5")
            )
        
        return validation_result
    
    async def _store_record(
        self,
        record: ComprehensiveTradeRecord,
        validation_result: Optional[DataValidationResult]
    ) -> bool:
        """Store trade record (with quarantine if needed)."""
        
        try:
            # Determine storage location based on validation
            if validation_result and validation_result.recommendations:
                if validation_result.recommendations.quarantine:
                    # Store in quarantine
                    logger.info(f"Quarantining record {record.id} due to quality issues")
                    self.metrics.quarantined_records += 1
                    # In real implementation: store in quarantine table
                    return True
            
            # Store in main storage
            # In real implementation: self.storage_manager.store_record(record)
            
            if record.learning_metadata.learning_eligible:
                self.metrics.learning_eligible_records += 1
            
            self.metrics.valid_records += 1
            return True
            
        except Exception as e:
            logger.error(f"Storage error for record {record.id}: {str(e)}")
            return False
    
    def _update_metrics(
        self,
        start_time: datetime,
        record: ComprehensiveTradeRecord,
        validation_result: Optional[DataValidationResult]
    ):
        """Update pipeline metrics."""
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        self.metrics.total_records_processed += 1
        self.metrics.last_processed_timestamp = datetime.now()
        
        # Update average processing time
        if self.metrics.total_records_processed == 1:
            self.metrics.average_processing_time_ms = Decimal(str(processing_time))
        else:
            # Calculate rolling average
            current_avg = self.metrics.average_processing_time_ms
            new_avg = (current_avg * Decimal(str(self.metrics.total_records_processed - 1)) + 
                      Decimal(str(processing_time))) / Decimal(str(self.metrics.total_records_processed))
            self.metrics.average_processing_time_ms = new_avg
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics."""
        
        return {
            "total_records_processed": self.metrics.total_records_processed,
            "valid_records": self.metrics.valid_records,
            "quarantined_records": self.metrics.quarantined_records,
            "learning_eligible_records": self.metrics.learning_eligible_records,
            "processing_errors": self.metrics.processing_errors,
            "average_processing_time_ms": float(self.metrics.average_processing_time_ms),
            "last_processed": self.metrics.last_processed_timestamp.isoformat() if self.metrics.last_processed_timestamp else None,
            "validation_pass_rate": self.metrics.valid_records / max(self.metrics.total_records_processed, 1),
            "learning_eligibility_rate": self.metrics.learning_eligible_records / max(self.metrics.total_records_processed, 1)
        }
    
    async def generate_quality_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive data quality report."""
        
        # In real implementation, would query stored validation results
        validation_results = []  # Would fetch from database
        
        return self.validation_reporter.generate_validation_report(
            validation_results, start_time, end_time
        )