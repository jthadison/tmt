"""
Continuous Improvement Pipeline Agent

This agent implements a sophisticated continuous improvement system that enables
the trading platform to systematically test, validate, and deploy improvements
while maintaining safety and statistical rigor.

Key Components:
- Shadow Testing Engine: Risk-free strategy testing
- Gradual Rollout Manager: Phased deployment with statistical validation
- Performance Comparison: Advanced A/B testing with control groups
- Automatic Rollback: Safety mechanisms for immediate intervention
- Improvement Suggestions: AI-driven optimization recommendations
- Monthly Reporting: Executive-level insights and progress tracking
"""

# Export main components for easier imports
try:
    from .pipeline_orchestrator import ContinuousImprovementOrchestrator
    from .shadow_testing_engine import ShadowTestingEngine
    from .gradual_rollout_manager import GradualRolloutManager
    from .performance_comparator import PerformanceComparator
    from .automatic_rollback_manager import AutomaticRollbackManager
    from .improvement_suggestion_engine import ImprovementSuggestionEngine
    from .optimization_report_generator import OptimizationReportGenerator
    from .models import *
except ImportError:
    # Allow for direct module imports during testing
    pass

__all__ = [
    'ContinuousImprovementOrchestrator',
    'ShadowTestingEngine', 
    'GradualRolloutManager',
    'PerformanceComparator',
    'AutomaticRollbackManager',
    'ImprovementSuggestionEngine',
    'OptimizationReportGenerator'
]