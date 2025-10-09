"""
Tests for Report Generator - Story 11.7
"""

import pytest
import json
from datetime import datetime

from app.report_generator import ReportGenerator
from app.models import ValidationStatus


class TestReportGenerator:
    """Test report generation functionality"""

    def test_generator_initialization(self):
        """Test report generator initialization"""
        generator = ReportGenerator()
        assert generator is not None

    def test_generate_json_report(self, sample_validation_report):
        """Test JSON report generation"""
        generator = ReportGenerator()

        json_report = generator.generate_json_report(sample_validation_report)

        # Should be valid JSON
        parsed = json.loads(json_report)
        assert parsed['job_id'] == "test-job-123"
        assert parsed['status'] == "APPROVED"
        assert parsed['all_checks_passed'] is True

    def test_generate_markdown_report(self, sample_validation_report):
        """Test Markdown report generation"""
        generator = ReportGenerator()

        md_report = generator.generate_markdown_report(sample_validation_report)

        # Should contain expected sections
        assert "## ✅ Parameter Validation Results" in md_report
        assert "### Validation Checks" in md_report
        assert "#### 1. Schema Validation" in md_report
        assert "#### 2. Overfitting Score" in md_report
        assert "#### 3. Walk-Forward Backtest" in md_report
        assert "#### 4. Monte Carlo Simulation" in md_report
        assert "#### 5. Stress Testing" in md_report
        assert "### Overall Result" in md_report

        # Should contain job ID
        assert "test-job-123" in md_report

    def test_markdown_report_approved_status(self, sample_validation_report):
        """Test Markdown report for approved validation"""
        generator = ReportGenerator()

        md_report = generator.generate_markdown_report(sample_validation_report)

        # Should indicate approval
        assert "APPROVED FOR DEPLOYMENT" in md_report
        assert "✅" in md_report

    def test_markdown_report_rejected_status(self, sample_validation_report):
        """Test Markdown report for rejected validation"""
        generator = ReportGenerator()

        # Modify report to rejected status
        sample_validation_report.status = ValidationStatus.REJECTED
        sample_validation_report.all_checks_passed = False
        sample_validation_report.recommendations = [
            "Fix schema validation errors",
            "Reduce overfitting score"
        ]

        md_report = generator.generate_markdown_report(sample_validation_report)

        # Should indicate rejection
        assert "DEPLOYMENT BLOCKED" in md_report
        assert "❌" in md_report

        # Should include recommendations
        assert "### Recommendations" in md_report
        assert "Fix schema validation errors" in md_report

    def test_format_schema_validation_passed(self, sample_validation_report):
        """Test formatting passed schema validation"""
        generator = ReportGenerator()

        formatted = generator._format_schema_validation(
            sample_validation_report.schema_validation
        )

        assert "✅ PASSED" in formatted
        assert "Configuration adheres to JSON schema" in formatted

    def test_format_schema_validation_failed(self):
        """Test formatting failed schema validation"""
        from app.models import SchemaValidationResult

        generator = ReportGenerator()

        failed_result = SchemaValidationResult(
            passed=False,
            errors=["Missing required field: version", "Invalid type for confidence_threshold"],
            warnings=["Deprecated field used: old_param"]
        )

        formatted = generator._format_schema_validation(failed_result)

        assert "❌ FAILED" in formatted
        assert "Missing required field: version" in formatted
        assert "Invalid type for confidence_threshold" in formatted
        assert "Deprecated field used: old_param" in formatted

    def test_format_walkforward_validation(self, sample_validation_report):
        """Test formatting walk-forward validation results"""
        generator = ReportGenerator()

        formatted = generator._format_walkforward_validation(
            sample_validation_report.walk_forward_validation
        )

        # Should include table with metrics
        assert "| Metric | Value | Threshold | Status |" in formatted
        assert "Out-of-Sample Sharpe" in formatted
        assert "Max Drawdown" in formatted
        assert "Win Rate" in formatted
        assert "Profit Factor" in formatted

    def test_format_montecarlo_validation(self, sample_validation_report):
        """Test formatting Monte Carlo validation results"""
        generator = ReportGenerator()

        formatted = generator._format_montecarlo_validation(
            sample_validation_report.monte_carlo_validation
        )

        # Should include confidence intervals
        assert "95% Confidence Interval" in formatted
        assert "Sharpe Ratio" in formatted
        assert "[1.10, 1.60]" in formatted

    def test_save_report_json(self, sample_validation_report, tmp_path):
        """Test saving JSON report to file"""
        generator = ReportGenerator()

        output_file = tmp_path / "test_report.json"

        generator.save_report(
            sample_validation_report,
            str(output_file),
            format="json"
        )

        # File should exist
        assert output_file.exists()

        # Should be valid JSON
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert data['job_id'] == "test-job-123"

    def test_save_report_markdown(self, sample_validation_report, tmp_path):
        """Test saving Markdown report to file"""
        generator = ReportGenerator()

        output_file = tmp_path / "test_report.md"

        generator.save_report(
            sample_validation_report,
            str(output_file),
            format="markdown"
        )

        # File should exist
        assert output_file.exists()

        # Should contain Markdown content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "## ✅ Parameter Validation Results" in content

    def test_save_report_invalid_format(self, sample_validation_report, tmp_path):
        """Test error handling for invalid format"""
        generator = ReportGenerator()

        output_file = tmp_path / "test_report.txt"

        with pytest.raises(ValueError) as exc_info:
            generator.save_report(
                sample_validation_report,
                str(output_file),
                format="invalid"
            )

        assert "Unsupported format" in str(exc_info.value)

    def test_markdown_report_with_warnings(self):
        """Test Markdown report includes warnings"""
        from app.models import (
            ValidationReport, SchemaValidationResult,
            OverfittingValidationResult, WalkForwardValidationResult,
            MonteCarloValidationResult, StressTestValidationResult,
            AcceptanceCriteriaValidation
        )

        generator = ReportGenerator()

        schema_result = SchemaValidationResult(
            passed=True,
            errors=[],
            warnings=["Parameter close to threshold", "Consider review"]
        )

        report = ValidationReport(
            job_id="test-123",
            config_file="test.yaml",
            timestamp=datetime.utcnow(),
            status=ValidationStatus.APPROVED,
            duration_seconds=100.0,
            schema_validation=schema_result,
            overfitting_validation=OverfittingValidationResult(
                passed=True, overfitting_score=0.2, threshold=0.3, message="OK"
            ),
            walk_forward_validation=WalkForwardValidationResult(
                passed=True, in_sample_sharpe=1.5, out_of_sample_sharpe=1.3,
                max_drawdown=0.1, win_rate=0.5, profit_factor=1.4,
                num_trades=50, avg_out_of_sample_sharpe=1.3, message="OK"
            ),
            monte_carlo_validation=MonteCarloValidationResult(
                passed=True, num_runs=1000, sharpe_mean=1.3, sharpe_std=0.1,
                sharpe_95ci_lower=1.1, sharpe_95ci_upper=1.5,
                drawdown_95ci_lower=0.08, drawdown_95ci_upper=0.15,
                win_rate_95ci_lower=0.45, win_rate_95ci_upper=0.55,
                threshold=0.8, message="OK"
            ),
            stress_test_validation=StressTestValidationResult(
                passed=True, crisis_results=[], message="OK"
            ),
            acceptance_criteria=AcceptanceCriteriaValidation(
                passed=True, all_criteria=[], passed_count=8, failed_count=0
            ),
            all_checks_passed=True,
            recommendations=[]
        )

        md_report = generator.generate_markdown_report(report)

        # Should include warnings
        assert "Warnings" in md_report
        assert "Parameter close to threshold" in md_report
