"""
Report Generator - Story 11.7, Task 5

Generates validation reports in JSON and Markdown formats for
CI/CD integration and human review.
"""

import json
from typing import Dict, List, Any
from datetime import datetime
import logging

from .models import ValidationReport, ValidationStatus

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates validation reports in multiple formats

    Formats:
    - JSON: For programmatic consumption and storage
    - Markdown: For GitHub PR comments and human review
    """

    def generate_json_report(self, report: ValidationReport) -> str:
        """
        Generate JSON format report

        Args:
            report: Validation report

        Returns:
            JSON string
        """
        return report.model_dump_json(indent=2)

    def generate_markdown_report(self, report: ValidationReport) -> str:
        """
        Generate Markdown format report for PR comments

        Args:
            report: Validation report

        Returns:
            Markdown formatted string
        """
        # Status emoji
        status_emoji = {
            ValidationStatus.APPROVED: "✅",
            ValidationStatus.REJECTED: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.IN_PROGRESS: "🔄",
            ValidationStatus.FAILED: "💥"
        }

        emoji = status_emoji.get(report.status, "❓")

        md = f"""## {emoji} Parameter Validation Results

**Configuration**: `{report.config_file}`
**Status**: **{report.status.value}**
**Duration**: {report.duration_seconds:.1f}s
**Timestamp**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

### Validation Checks

"""

        # Schema Validation
        md += self._format_schema_validation(report.schema_validation)

        # Overfitting Score
        md += self._format_overfitting_validation(report.overfitting_validation)

        # Walk-Forward Backtest
        md += self._format_walkforward_validation(report.walk_forward_validation)

        # Monte Carlo Simulation
        md += self._format_montecarlo_validation(report.monte_carlo_validation)

        # Stress Testing
        md += self._format_stress_test_validation(report.stress_test_validation)

        # Acceptance Criteria Summary
        md += self._format_acceptance_criteria(report.acceptance_criteria)

        # Overall Result
        md += "\n---\n\n### Overall Result\n\n"

        if report.all_checks_passed:
            md += "✅ **APPROVED FOR DEPLOYMENT**\n\n"
            md += "All validation checks passed. Parameters are ready for production deployment.\n"
        else:
            md += "❌ **DEPLOYMENT BLOCKED**\n\n"
            md += "One or more validation checks failed. Review the results above and address issues.\n"

        # Recommendations
        if report.recommendations:
            md += "\n### Recommendations\n\n"
            for rec in report.recommendations:
                md += f"- {rec}\n"

        # Footer
        md += f"\n---\n\n*Validation Job ID: `{report.job_id}`*\n"

        return md

    def _format_schema_validation(self, result) -> str:
        """Format schema validation section"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"

        md = f"#### 1. Schema Validation: {status}\n\n"

        if result.passed:
            md += "Configuration adheres to JSON schema.\n\n"
        else:
            md += "**Errors:**\n"
            for error in result.errors:
                md += f"- ❌ {error}\n"

        if result.warnings:
            md += "\n**Warnings:**\n"
            for warning in result.warnings:
                md += f"- ⚠️ {warning}\n"

        md += "\n"
        return md

    def _format_overfitting_validation(self, result) -> str:
        """Format overfitting validation section"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"

        md = f"#### 2. Overfitting Score: {status}\n\n"
        md += f"- **Score**: {result.overfitting_score:.3f}\n"
        md += f"- **Threshold**: < {result.threshold:.3f}\n"
        md += f"- **Result**: {result.message}\n\n"

        return md

    def _format_walkforward_validation(self, result) -> str:
        """Format walk-forward validation section"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"

        md = f"#### 3. Walk-Forward Backtest (6 months): {status}\n\n"

        md += "| Metric | Value | Threshold | Status |\n"
        md += "|--------|-------|-----------|--------|\n"

        # Out-of-sample Sharpe
        sharpe_status = "✅" if result.out_of_sample_sharpe >= 1.0 else "❌"
        md += f"| Out-of-Sample Sharpe | {result.out_of_sample_sharpe:.2f} | ≥ 1.0 | {sharpe_status} |\n"

        # Max Drawdown
        dd_status = "✅" if result.max_drawdown < 0.20 else "❌"
        md += f"| Max Drawdown | {result.max_drawdown*100:.1f}% | < 20% | {dd_status} |\n"

        # Win Rate
        wr_status = "✅" if result.win_rate >= 0.45 else "❌"
        md += f"| Win Rate | {result.win_rate*100:.1f}% | ≥ 45% | {wr_status} |\n"

        # Profit Factor
        pf_status = "✅" if result.profit_factor >= 1.3 else "❌"
        md += f"| Profit Factor | {result.profit_factor:.2f} | ≥ 1.3 | {pf_status} |\n"

        md += f"\n**Total Trades**: {result.num_trades}\n\n"

        return md

    def _format_montecarlo_validation(self, result) -> str:
        """Format Monte Carlo validation section"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"

        md = f"#### 4. Monte Carlo Simulation ({result.num_runs} runs): {status}\n\n"

        md += "| Metric | 95% Confidence Interval | Status |\n"
        md += "|--------|------------------------|--------|\n"

        # Sharpe Ratio
        sharpe_status = "✅" if result.sharpe_95ci_lower >= result.threshold else "❌"
        md += f"| Sharpe Ratio | [{result.sharpe_95ci_lower:.2f}, {result.sharpe_95ci_upper:.2f}] | {sharpe_status} |\n"

        # Max Drawdown
        md += f"| Max Drawdown | [{result.drawdown_95ci_lower*100:.1f}%, {result.drawdown_95ci_upper*100:.1f}%] | ℹ️ |\n"

        # Win Rate
        md += f"| Win Rate | [{result.win_rate_95ci_lower*100:.1f}%, {result.win_rate_95ci_upper*100:.1f}%] | ℹ️ |\n"

        md += f"\n**Mean Sharpe**: {result.sharpe_mean:.2f} ± {result.sharpe_std:.2f}\n"
        md += f"**Lower Bound Threshold**: ≥ {result.threshold:.2f}\n\n"

        return md

    def _format_stress_test_validation(self, result) -> str:
        """Format stress test validation section"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"

        md = f"#### 5. Stress Testing: {status}\n\n"

        md += "| Crisis Period | Max Drawdown | Recovery Days | Status |\n"
        md += "|---------------|--------------|---------------|--------|\n"

        for crisis in result.crisis_results:
            crisis_status = "✅" if crisis.passed else "❌"
            dd_str = f"{crisis.max_drawdown*100:.1f}%"
            recovery_str = f"{crisis.recovery_days} days" if crisis.recovery_days else "N/A"

            md += f"| {crisis.crisis_name} | {dd_str} | {recovery_str} | {crisis_status} |\n"

        md += f"\n**Summary**: {result.message}\n\n"

        return md

    def _format_acceptance_criteria(self, result) -> str:
        """Format acceptance criteria section"""
        md = "#### 6. Acceptance Criteria Summary\n\n"

        md += f"**Overall**: {result.passed_count}/{len(result.all_criteria)} criteria passed\n\n"

        if result.passed:
            md += "✅ All acceptance criteria met!\n\n"
        else:
            md += "❌ Some criteria not met:\n\n"

            for criterion in result.all_criteria:
                if not criterion.passed:
                    status = "❌"
                    md += f"- {status} **{criterion.criterion}**: {criterion.message}\n"

        md += "\n"
        return md

    def save_report(
        self,
        report: ValidationReport,
        output_file: str,
        format: str = "json"
    ) -> None:
        """
        Save report to file

        Args:
            report: Validation report
            output_file: Output file path
            format: Output format ('json' or 'markdown')
        """
        if format == "json":
            content = self.generate_json_report(report)
        elif format == "markdown":
            content = self.generate_markdown_report(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Report saved to {output_file}")
