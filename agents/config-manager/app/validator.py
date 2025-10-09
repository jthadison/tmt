"""
Configuration Validator

Validates trading configurations against JSON Schema and business rules.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any
import yaml
from jsonschema import validate, ValidationError, Draft7Validator
from .models import TradingConfig, ConfigValidationResult

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Validates trading configurations

    Features:
    - JSON Schema validation
    - Business rule validation
    - Cross-field validation
    - Constraint checking
    """

    def __init__(self, schema_path: Path):
        """
        Initialize validator

        Args:
            schema_path: Path to JSON Schema file
        """
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)

        logger.info(f"ConfigValidator initialized with schema: {schema_path}")

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON Schema from file"""
        try:
            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
            logger.debug(f"Loaded schema from {self.schema_path}")
            return schema
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            raise

    def validate_file(self, config_path: Path) -> ConfigValidationResult:
        """
        Validate configuration file

        Args:
            config_path: Path to configuration YAML file

        Returns:
            ConfigValidationResult with validation status
        """
        errors = []
        warnings = []
        schema_valid = False
        constraints_valid = False

        try:
            # Load YAML file
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            # Validate against JSON Schema
            schema_errors = self._validate_schema(config_data)
            if schema_errors:
                errors.extend(schema_errors)
                schema_valid = False
            else:
                schema_valid = True

            # Parse into Pydantic model
            try:
                config = TradingConfig(**config_data)

                # Validate constraints
                constraint_errors = config.validate_constraints()
                if constraint_errors:
                    errors.extend(constraint_errors)
                    constraints_valid = False
                else:
                    constraints_valid = True

                # Additional business rule validations
                business_warnings = self._validate_business_rules(config)
                warnings.extend(business_warnings)

            except Exception as e:
                errors.append(f"Pydantic validation error: {str(e)}")
                constraints_valid = False

        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
        except FileNotFoundError:
            errors.append(f"Configuration file not found: {config_path}")
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            logger.error(f"Validation error: {e}", exc_info=True)

        valid = (len(errors) == 0)

        return ConfigValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            schema_valid=schema_valid,
            constraints_valid=constraints_valid
        )

    def _validate_schema(self, config_data: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against JSON Schema

        Args:
            config_data: Configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            # Use Draft7Validator for detailed error messages
            for error in self.validator.iter_errors(config_data):
                # Build error path
                path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                error_msg = f"{path}: {error.message}"
                errors.append(error_msg)

        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
            logger.error(f"Schema validation failed: {e}", exc_info=True)

        return errors

    def _validate_business_rules(self, config: TradingConfig) -> List[str]:
        """
        Validate business rules

        Args:
            config: Trading configuration

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for large deviations (warning, not error)
        for session_name, session in config.session_parameters.items():
            confidence_pct_deviation = (
                (session.confidence_threshold - config.baseline.confidence_threshold) /
                config.baseline.confidence_threshold * 100
            )

            if abs(confidence_pct_deviation) > 50:
                warnings.append(
                    f"Session '{session_name}': Large confidence deviation "
                    f"({confidence_pct_deviation:.1f}%) from baseline"
                )

            # Check risk-reward ratio reasonableness
            if session.min_risk_reward > 10:
                warnings.append(
                    f"Session '{session_name}': Very high risk-reward ratio "
                    f"({session.min_risk_reward:.1f}) may be difficult to achieve"
                )

        # Check validation metrics if present
        if config.validation:
            # Warn if out-of-sample much worse than in-sample
            if (config.validation.backtest_sharpe and
                config.validation.out_of_sample_sharpe):
                ratio = (config.validation.out_of_sample_sharpe /
                        config.validation.backtest_sharpe)
                if ratio < 0.5:
                    warnings.append(
                        f"Out-of-sample Sharpe ({config.validation.out_of_sample_sharpe:.2f}) "
                        f"significantly worse than backtest ({config.validation.backtest_sharpe:.2f}). "
                        "Possible overfitting."
                    )

            # Warn on high overfitting score
            if config.validation.overfitting_score:
                if 0.25 < config.validation.overfitting_score <= 0.3:
                    warnings.append(
                        f"Overfitting score ({config.validation.overfitting_score:.3f}) "
                        "approaching critical threshold"
                    )

        # Check for missing recommended fields
        if not config.validation:
            warnings.append("No validation metrics provided (recommended for production)")

        for session_name, session in config.session_parameters.items():
            if not session.justification:
                warnings.append(
                    f"Session '{session_name}': No justification provided (recommended)"
                )

        return warnings

    def validate_yaml_syntax(self, config_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate YAML syntax only (quick check)

        Args:
            config_path: Path to YAML file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            with open(config_path, 'r') as f:
                yaml.safe_load(f)
            return True, []
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
            return False, errors
        except FileNotFoundError:
            errors.append(f"File not found: {config_path}")
            return False, errors
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
            return False, errors


def validate_config_file(config_path: str, schema_path: str = None) -> ConfigValidationResult:
    """
    Standalone function to validate a configuration file

    Args:
        config_path: Path to configuration YAML file
        schema_path: Path to JSON Schema (default: config/parameters/schema.json)

    Returns:
        ConfigValidationResult
    """
    if schema_path is None:
        # Default schema path
        repo_root = Path(__file__).parent.parent.parent.parent
        schema_path = repo_root / "config" / "parameters" / "schema.json"

    validator = ConfigValidator(Path(schema_path))
    return validator.validate_file(Path(config_path))


if __name__ == "__main__":
    """CLI for standalone validation"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Validate trading configuration")
    parser.add_argument("config_file", help="Path to configuration YAML file")
    parser.add_argument(
        "--schema",
        help="Path to JSON Schema file",
        default=None
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation output"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    # Validate
    result = validate_config_file(args.config_file, args.schema)

    # Output results
    if result.valid:
        print(f"✓ Configuration valid: {args.config_file}")
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
        sys.exit(0)
    else:
        print(f"✗ Configuration invalid: {args.config_file}")
        print("\nErrors:")
        for error in result.errors:
            print(f"  ✗ {error}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")

        sys.exit(1)
