"""
Data Collection Agent

This agent implements a comprehensive data collection pipeline that captures
all aspects of trading performance for learning and optimization purposes.
"""

from .data_models import (
    ComprehensiveTradeRecord,
    PatternPerformance,
    ExecutionQualityMetrics,
    FalseSignalAnalysis,
    DataValidationResult,
)
from .pipeline import DataCollectionPipeline
from .feature_extractors import (
    MarketConditionExtractor,
    SignalContextExtractor,
    ExecutionQualityExtractor,
    PersonalityImpactExtractor,
    PerformanceCalculator,
)
from .validators import (
    DataCompletenessValidator,
    DataConsistencyValidator,
    AnomalyDetectionValidator,
    TimingValidationValidator,
)

__all__ = [
    "ComprehensiveTradeRecord",
    "PatternPerformance",
    "ExecutionQualityMetrics",
    "FalseSignalAnalysis",
    "DataValidationResult",
    "DataCollectionPipeline",
    "MarketConditionExtractor",
    "SignalContextExtractor",
    "ExecutionQualityExtractor",
    "PersonalityImpactExtractor",
    "PerformanceCalculator",
    "DataCompletenessValidator",
    "DataConsistencyValidator",
    "AnomalyDetectionValidator",
    "TimingValidationValidator",
]