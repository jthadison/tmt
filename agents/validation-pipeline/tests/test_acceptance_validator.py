"""
Tests for Acceptance Criteria Validator - Story 11.7
"""

import pytest

from app.acceptance_validator import AcceptanceCriteriaValidator
from app.models import (
    SchemaValidationResult, OverfittingValidationResult,
    WalkForwardValidationResult, MonteCarloValidationResult,
    StressTestValidationResult, StressTestResult
)


class TestAcceptanceCriteriaValidator:
    """Test acceptance criteria validation functionality"""

    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = AcceptanceCriteriaValidator()
        assert validator is not None

    def test_all_criteria_pass(self):
        """Test when all acceptance criteria pass"""
        validator = AcceptanceCriteriaValidator()

        schema_result = SchemaValidationResult(passed=True, errors=[], warnings=[])
        overfitting_result = OverfittingValidationResult(
            passed=True, overfitting_score=0.25, threshold=0.3, message="OK"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=True, in_sample_sharpe=1.5, out_of_sample_sharpe=1.3,
            max_drawdown=0.15, win_rate=0.50, profit_factor=1.4,
            num_trades=50, avg_out_of_sample_sharpe=1.3, message="OK"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.15,
            sharpe_95ci_lower=1.0, sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
            threshold=0.8, message="OK"
        )
        stress_test_result = StressTestValidationResult(
            passed=True, crisis_results=[], message="OK"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        assert result.passed is True
        assert result.passed_count == 8
        assert result.failed_count == 0
        assert len(result.all_criteria) == 8

    def test_schema_validation_failure(self):
        """Test when schema validation fails"""
        validator = AcceptanceCriteriaValidator()

        schema_result = SchemaValidationResult(
            passed=False, errors=["Invalid field"], warnings=[]
        )
        overfitting_result = OverfittingValidationResult(
            passed=True, overfitting_score=0.25, threshold=0.3, message="OK"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=True, in_sample_sharpe=1.5, out_of_sample_sharpe=1.3,
            max_drawdown=0.15, win_rate=0.50, profit_factor=1.4,
            num_trades=50, avg_out_of_sample_sharpe=1.3, message="OK"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.15,
            sharpe_95ci_lower=1.0, sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
            threshold=0.8, message="OK"
        )
        stress_test_result = StressTestValidationResult(
            passed=True, crisis_results=[], message="OK"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        assert result.passed is False
        assert result.failed_count >= 1

        # Check that schema criterion failed
        schema_criterion = next(c for c in result.all_criteria if c.criterion == "Schema Validation")
        assert schema_criterion.passed is False

    def test_overfitting_score_failure(self):
        """Test when overfitting score exceeds threshold"""
        validator = AcceptanceCriteriaValidator()

        schema_result = SchemaValidationResult(passed=True, errors=[], warnings=[])
        overfitting_result = OverfittingValidationResult(
            passed=False, overfitting_score=0.45, threshold=0.3, message="Failed"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=True, in_sample_sharpe=1.5, out_of_sample_sharpe=1.3,
            max_drawdown=0.15, win_rate=0.50, profit_factor=1.4,
            num_trades=50, avg_out_of_sample_sharpe=1.3, message="OK"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.15,
            sharpe_95ci_lower=1.0, sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
            threshold=0.8, message="OK"
        )
        stress_test_result = StressTestValidationResult(
            passed=True, crisis_results=[], message="OK"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        assert result.passed is False

        # Check overfitting criterion
        overfitting_criterion = next(c for c in result.all_criteria if c.criterion == "Overfitting Score")
        assert overfitting_criterion.passed is False
        assert overfitting_criterion.actual_value == 0.45
        assert overfitting_criterion.threshold == 0.3

    def test_sharpe_ratio_failure(self):
        """Test when Sharpe ratio is below threshold"""
        validator = AcceptanceCriteriaValidator()

        schema_result = SchemaValidationResult(passed=True, errors=[], warnings=[])
        overfitting_result = OverfittingValidationResult(
            passed=True, overfitting_score=0.25, threshold=0.3, message="OK"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=False, in_sample_sharpe=1.5, out_of_sample_sharpe=0.8,  # Below 1.0
            max_drawdown=0.15, win_rate=0.50, profit_factor=1.4,
            num_trades=50, avg_out_of_sample_sharpe=0.8, message="Failed"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.15,
            sharpe_95ci_lower=1.0, sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
            threshold=0.8, message="OK"
        )
        stress_test_result = StressTestValidationResult(
            passed=True, crisis_results=[], message="OK"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        assert result.passed is False

        sharpe_criterion = next(c for c in result.all_criteria if c.criterion == "Out-of-Sample Sharpe Ratio")
        assert sharpe_criterion.passed is False

    def test_stress_test_failure(self):
        """Test when stress tests fail"""
        validator = AcceptanceCriteriaValidator()

        schema_result = SchemaValidationResult(passed=True, errors=[], warnings=[])
        overfitting_result = OverfittingValidationResult(
            passed=True, overfitting_score=0.25, threshold=0.3, message="OK"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=True, in_sample_sharpe=1.5, out_of_sample_sharpe=1.3,
            max_drawdown=0.15, win_rate=0.50, profit_factor=1.4,
            num_trades=50, avg_out_of_sample_sharpe=1.3, message="OK"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.15,
            sharpe_95ci_lower=1.0, sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
            threshold=0.8, message="OK"
        )

        # Failed stress test
        failed_crisis = StressTestResult(
            crisis_name="2008 Crisis",
            passed=False,
            max_drawdown=0.30,
            max_drawdown_threshold=0.25,
            recovery_days=None,
            recovery_threshold=90,
            num_trades=10,
            message="Exceeded drawdown threshold"
        )

        stress_test_result = StressTestValidationResult(
            passed=False, crisis_results=[failed_crisis], message="Failed"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        assert result.passed is False

        stress_criterion = next(c for c in result.all_criteria if c.criterion == "Stress Testing")
        assert stress_criterion.passed is False

    def test_generate_remediation_suggestions(self):
        """Test remediation suggestion generation"""
        validator = AcceptanceCriteriaValidator()

        # Create failing results
        schema_result = SchemaValidationResult(
            passed=False, errors=["Invalid"], warnings=[]
        )
        overfitting_result = OverfittingValidationResult(
            passed=False, overfitting_score=0.45, threshold=0.3, message="Failed"
        )
        walkforward_result = WalkForwardValidationResult(
            passed=False, in_sample_sharpe=1.5, out_of_sample_sharpe=0.8,
            max_drawdown=0.25, win_rate=0.40, profit_factor=1.1,
            num_trades=50, avg_out_of_sample_sharpe=0.8, message="Failed"
        )
        montecarlo_result = MonteCarloValidationResult(
            passed=False, num_runs=1000, sharpe_mean=0.7, sharpe_std=0.15,
            sharpe_95ci_lower=0.5, sharpe_95ci_upper=0.9,
            drawdown_95ci_lower=0.10, drawdown_95ci_upper=0.20,
            win_rate_95ci_lower=0.35, win_rate_95ci_upper=0.45,
            threshold=0.8, message="Failed"
        )
        stress_test_result = StressTestValidationResult(
            passed=False, crisis_results=[], message="Failed"
        )

        result = validator.validate_all_criteria(
            schema_result, overfitting_result, walkforward_result,
            montecarlo_result, stress_test_result
        )

        suggestions = validator.generate_remediation_suggestions(result)

        # Should have multiple suggestions for failed criteria
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)

    def test_remediation_for_specific_failures(self):
        """Test remediation suggestions for specific failure types"""
        validator = AcceptanceCriteriaValidator()

        # Test each criterion's remediation
        from app.models import AcceptanceCriteriaResult

        schema_failure = AcceptanceCriteriaResult(
            criterion="Schema Validation",
            passed=False,
            actual_value=0.0,
            threshold=1.0,
            operator="==",
            message="Failed"
        )

        remediation = validator._get_remediation_for_criterion(schema_failure)
        assert "schema" in remediation.lower()

        overfitting_failure = AcceptanceCriteriaResult(
            criterion="Overfitting Score",
            passed=False,
            actual_value=0.45,
            threshold=0.3,
            operator="<",
            message="Failed"
        )

        remediation = validator._get_remediation_for_criterion(overfitting_failure)
        assert "overfitting" in remediation.lower()
