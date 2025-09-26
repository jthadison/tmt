"""
Production Validation Framework

Detects and prevents random number usage in production trading components.
Provides runtime validation and audit capabilities.
"""

import os
import sys
import logging
import inspect
import traceback
import functools
from typing import Set, List, Dict, Any, Callable, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProductionViolation(Exception):
    """Exception raised when production safety rules are violated"""
    pass


class RandomUsageDetector:
    """Detects random number usage in production environments"""

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []
        self.allowed_files: Set[str] = {
            # Files allowed to use random (for statistical modeling)
            "monte_carlo_projections.py",
            "test_",  # All test files
            "mock_",  # Mock implementations
            "simulation",  # Simulation components
        }

        self.critical_components: Set[str] = {
            # Components that must never use random in production
            "signal_generator",
            "pattern_detection",
            "decision_generator",
            "execution_engine",
            "market_analysis",
            "orchestrator",
            "stream_manager"
        }

    def is_file_allowed(self, filename: str) -> bool:
        """Check if file is allowed to use random"""
        filename_lower = filename.lower()

        # Allow test files and mocks
        for allowed in self.allowed_files:
            if allowed in filename_lower:
                return True

        return False

    def is_critical_component(self, filename: str) -> bool:
        """Check if file is a critical trading component"""
        filename_lower = filename.lower()

        for component in self.critical_components:
            if component in filename_lower:
                return True

        return False

    def detect_random_import(self) -> List[Dict[str, Any]]:
        """Detect random imports in the call stack"""
        violations = []

        # Get current call stack
        stack = traceback.extract_stack()

        for frame in stack:
            filename = Path(frame.filename).name

            # Skip allowed files
            if self.is_file_allowed(filename):
                continue

            # Check if this is a critical component
            if self.is_critical_component(filename):
                # Read the file and check for random imports
                try:
                    with open(frame.filename, 'r', encoding='utf-8') as f:
                        content = f.read()

                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        line_clean = line.strip()

                        # Check for random imports
                        if (line_clean.startswith('import random') or
                            line_clean.startswith('from random import') or
                            'random.' in line_clean):

                            violations.append({
                                "type": "random_usage",
                                "file": filename,
                                "line": line_num,
                                "code": line.strip(),
                                "severity": "critical" if self.is_critical_component(filename) else "warning"
                            })

                except Exception as e:
                    logger.debug(f"Could not analyze {filename}: {e}")

        return violations

    def validate_production_safety(self):
        """Validate production safety - raise exception if violations found"""
        from trading_config import get_trading_config

        config = get_trading_config()

        if not config.is_production_mode():
            return  # Only validate in production

        violations = self.detect_random_import()
        critical_violations = [v for v in violations if v["severity"] == "critical"]

        if critical_violations:
            error_msg = f"CRITICAL: Random usage detected in production mode:\n"
            for violation in critical_violations:
                error_msg += f"  {violation['file']}:{violation['line']} - {violation['code']}\n"

            logger.error(error_msg)
            raise ProductionViolation(error_msg)


# Global detector instance
_detector = RandomUsageDetector()


def validate_no_random_in_production():
    """Validate that random components are not used in production"""
    try:
        _detector.validate_production_safety()
    except ImportError:
        # Trading config not available, skip validation
        pass


def production_safe(func: Callable) -> Callable:
    """Decorator to mark functions as production-safe (no random usage allowed)"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Validate before function execution
        validate_no_random_in_production()

        # Execute function
        result = func(*args, **kwargs)

        return result

    return wrapper


async def production_safe_async(func: Callable) -> Callable:
    """Async decorator to mark functions as production-safe"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Validate before function execution
        validate_no_random_in_production()

        # Execute function
        result = await func(*args, **kwargs)

        return result

    return wrapper


class ProductionValidator:
    """Main production validation system"""

    def __init__(self):
        self.detector = RandomUsageDetector()
        self.audit_log: List[Dict[str, Any]] = []

    async def run_full_audit(self) -> Dict[str, Any]:
        """Run comprehensive audit of the trading system"""
        logger.info("Starting production validation audit...")

        audit_results = {
            "timestamp": str(logger.info),
            "random_violations": [],
            "critical_files_checked": [],
            "warnings": [],
            "status": "unknown"
        }

        try:
            # Check for random usage violations
            violations = self.detector.detect_random_import()
            audit_results["random_violations"] = violations

            # Categorize violations
            critical_violations = [v for v in violations if v["severity"] == "critical"]
            warning_violations = [v for v in violations if v["severity"] == "warning"]

            audit_results["warnings"] = warning_violations

            # Determine overall status
            if critical_violations:
                audit_results["status"] = "CRITICAL_VIOLATIONS"
                logger.error(f"Found {len(critical_violations)} critical random usage violations")
            elif warning_violations:
                audit_results["status"] = "WARNINGS"
                logger.warning(f"Found {len(warning_violations)} random usage warnings")
            else:
                audit_results["status"] = "CLEAN"
                logger.info("No random usage violations detected")

            # Log audit completion
            self.audit_log.append(audit_results)

        except Exception as e:
            audit_results["status"] = "ERROR"
            audit_results["error"] = str(e)
            logger.error(f"Audit failed: {e}")

        return audit_results

    def get_audit_history(self) -> List[Dict[str, Any]]:
        """Get history of all audits performed"""
        return self.audit_log.copy()


# Global validator instance
_validator = ProductionValidator()


async def run_production_audit() -> Dict[str, Any]:
    """Run comprehensive production audit"""
    return await _validator.run_full_audit()


def get_audit_history() -> List[Dict[str, Any]]:
    """Get audit history"""
    return _validator.get_audit_history()


# Runtime monitoring hook
def install_random_monitor():
    """Install runtime monitor to detect random usage"""
    import builtins

    # Store original random function
    original_random = __builtins__.get('random', None)

    def monitored_random(*args, **kwargs):
        """Monitored random function that validates usage"""
        validate_no_random_in_production()

        if original_random:
            return original_random(*args, **kwargs)
        else:
            raise RuntimeError("Random function not available")

    # Replace random in builtins (if it exists there)
    if original_random:
        __builtins__['random'] = monitored_random