"""
Walk-Forward Optimization Agent - Story 11.3

Main package exports for walk-forward optimization system.
"""

from .models import (
    WalkForwardConfig,
    WindowResult,
    WalkForwardResult,
    WindowType,
    OptimizationMethod,
    OptimizationJob,
    EquityPoint
)
from .optimizer import WalkForwardOptimizer
from .grid_search import ParameterGridGenerator, BayesianOptimizationWrapper
from .overfitting_detector import OverfittingDetector, OverfittingAlert
from .stability_analyzer import ParameterStabilityAnalyzer
from .validators import AcceptanceCriteriaValidator
from .report_generator import WalkForwardReportGenerator
from .visualization import VisualizationDataGenerator

__all__ = [
    # Models
    'WalkForwardConfig',
    'WindowResult',
    'WalkForwardResult',
    'WindowType',
    'OptimizationMethod',
    'OptimizationJob',
    'EquityPoint',

    # Core components
    'WalkForwardOptimizer',
    'ParameterGridGenerator',
    'BayesianOptimizationWrapper',
    'OverfittingDetector',
    'OverfittingAlert',
    'ParameterStabilityAnalyzer',
    'AcceptanceCriteriaValidator',
    'WalkForwardReportGenerator',
    'VisualizationDataGenerator',
]
