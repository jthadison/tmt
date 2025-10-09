"""
Acceptance Criteria Validator - Story 11.7, Task 6

Validates parameters against all acceptance criteria defined in AC2:
- Schema valid
- Overfitting score < 0.3
- Walk-forward out-of-sample Sharpe > 1.0
- Max drawdown < 20%
- Win rate > 45%
- Profit factor > 1.3
"""

import logging
from typing import List

from .models import (
    AcceptanceCriteriaResult,
    AcceptanceCriteriaValidation,
    SchemaValidationResult,
    OverfittingValidationResult,
    WalkForwardValidationResult,
    MonteCarloValidationResult,
    StressTestValidationResult
)

logger = logging.getLogger(__name__)


class AcceptanceCriteriaValidator:
    """
    Validates all acceptance criteria for parameter deployment

    Checks all criteria defined in Story 11.7 AC2:
    1. Schema validation passes
    2. Overfitting score < 0.3
    3. Walk-forward out-of-sample Sharpe > 1.0
    4. Max drawdown in backtest < 20%
    5. Win rate > 45%
    6. Profit factor > 1.3
    7. Monte Carlo lower bound Sharpe > 0.8
    8. Stress tests pass
    """

    def validate_all_criteria(
        self,
        schema_result: SchemaValidationResult,
        overfitting_result: OverfittingValidationResult,
        walkforward_result: WalkForwardValidationResult,
        montecarlo_result: MonteCarloValidationResult,
        stress_test_result: StressTestValidationResult
    ) -> AcceptanceCriteriaValidation:
        """
        Validate all acceptance criteria

        Args:
            schema_result: Schema validation result
            overfitting_result: Overfitting validation result
            walkforward_result: Walk-forward validation result
            montecarlo_result: Monte Carlo validation result
            stress_test_result: Stress test validation result

        Returns:
            Overall acceptance criteria validation
        """
        criteria: List[AcceptanceCriteriaResult] = []

        # 1. Schema Valid
        criteria.append(AcceptanceCriteriaResult(
            criterion="Schema Validation",
            passed=schema_result.passed,
            actual_value=1.0 if schema_result.passed else 0.0,
            threshold=1.0,
            operator="==",
            message="Configuration must adhere to JSON schema"
        ))

        # 2. Overfitting Score < 0.3
        criteria.append(AcceptanceCriteriaResult(
            criterion="Overfitting Score",
            passed=overfitting_result.passed,
            actual_value=overfitting_result.overfitting_score,
            threshold=0.3,
            operator="<",
            message=f"Overfitting score {overfitting_result.overfitting_score:.3f} {'meets' if overfitting_result.passed else 'exceeds'} threshold 0.3"
        ))

        # 3. Walk-Forward Out-of-Sample Sharpe > 1.0
        oos_sharpe_passed = walkforward_result.out_of_sample_sharpe >= 1.0
        criteria.append(AcceptanceCriteriaResult(
            criterion="Out-of-Sample Sharpe Ratio",
            passed=oos_sharpe_passed,
            actual_value=walkforward_result.out_of_sample_sharpe,
            threshold=1.0,
            operator=">=",
            message=f"Out-of-sample Sharpe {walkforward_result.out_of_sample_sharpe:.2f} {'meets' if oos_sharpe_passed else 'below'} threshold 1.0"
        ))

        # 4. Max Drawdown < 20%
        max_dd_passed = walkforward_result.max_drawdown < 0.20
        criteria.append(AcceptanceCriteriaResult(
            criterion="Maximum Drawdown",
            passed=max_dd_passed,
            actual_value=walkforward_result.max_drawdown * 100,
            threshold=20.0,
            operator="<",
            message=f"Max drawdown {walkforward_result.max_drawdown*100:.1f}% {'within' if max_dd_passed else 'exceeds'} threshold 20%"
        ))

        # 5. Win Rate > 45%
        win_rate_passed = walkforward_result.win_rate >= 0.45
        criteria.append(AcceptanceCriteriaResult(
            criterion="Win Rate",
            passed=win_rate_passed,
            actual_value=walkforward_result.win_rate * 100,
            threshold=45.0,
            operator=">=",
            message=f"Win rate {walkforward_result.win_rate*100:.1f}% {'meets' if win_rate_passed else 'below'} threshold 45%"
        ))

        # 6. Profit Factor > 1.3
        profit_factor_passed = walkforward_result.profit_factor >= 1.3
        criteria.append(AcceptanceCriteriaResult(
            criterion="Profit Factor",
            passed=profit_factor_passed,
            actual_value=walkforward_result.profit_factor,
            threshold=1.3,
            operator=">=",
            message=f"Profit factor {walkforward_result.profit_factor:.2f} {'meets' if profit_factor_passed else 'below'} threshold 1.3"
        ))

        # 7. Monte Carlo Lower Bound > 0.8
        mc_passed = montecarlo_result.sharpe_95ci_lower >= 0.8
        criteria.append(AcceptanceCriteriaResult(
            criterion="Monte Carlo Sharpe (95% CI Lower Bound)",
            passed=mc_passed,
            actual_value=montecarlo_result.sharpe_95ci_lower,
            threshold=0.8,
            operator=">=",
            message=f"Monte Carlo Sharpe 95% CI lower bound {montecarlo_result.sharpe_95ci_lower:.2f} {'meets' if mc_passed else 'below'} threshold 0.8"
        ))

        # 8. Stress Tests Pass
        stress_passed = stress_test_result.passed
        passed_count = sum(1 for r in stress_test_result.crisis_results if r.passed)
        total_count = len(stress_test_result.crisis_results)

        criteria.append(AcceptanceCriteriaResult(
            criterion="Stress Testing",
            passed=stress_passed,
            actual_value=float(passed_count),
            threshold=float(total_count),
            operator="==",
            message=f"Stress tests: {passed_count}/{total_count} crisis periods passed"
        ))

        # Calculate overall pass/fail
        passed_criteria = sum(1 for c in criteria if c.passed)
        all_passed = all(c.passed for c in criteria)

        return AcceptanceCriteriaValidation(
            passed=all_passed,
            all_criteria=criteria,
            passed_count=passed_criteria,
            failed_count=len(criteria) - passed_criteria
        )

    def generate_remediation_suggestions(
        self,
        validation: AcceptanceCriteriaValidation
    ) -> List[str]:
        """
        Generate remediation suggestions for failed criteria

        Args:
            validation: Acceptance criteria validation result

        Returns:
            List of remediation suggestions
        """
        suggestions = []

        for criterion in validation.all_criteria:
            if not criterion.passed:
                suggestion = self._get_remediation_for_criterion(criterion)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    def _get_remediation_for_criterion(
        self, criterion: AcceptanceCriteriaResult
    ) -> str:
        """Get remediation suggestion for a specific failed criterion"""

        remediation_map = {
            "Schema Validation": "Fix schema validation errors in configuration file. Check required fields and data types.",
            "Overfitting Score": "Reduce overfitting by: (1) Using more conservative parameters closer to baseline, (2) Increasing out-of-sample test period, (3) Reducing parameter complexity.",
            "Out-of-Sample Sharpe Ratio": "Improve out-of-sample performance by: (1) Testing parameters on longer historical periods, (2) Reducing parameter optimization, (3) Using more robust entry/exit rules.",
            "Maximum Drawdown": "Reduce drawdown by: (1) Tightening stop-loss levels, (2) Reducing position sizes, (3) Adding drawdown-based position scaling.",
            "Win Rate": "Improve win rate by: (1) Tightening entry criteria, (2) Improving signal quality filters, (3) Optimizing take-profit levels.",
            "Profit Factor": "Improve profit factor by: (1) Optimizing risk-reward ratio, (2) Cutting losses faster, (3) Letting winners run longer.",
            "Monte Carlo Sharpe (95% CI Lower Bound)": "Improve Monte Carlo robustness by: (1) Using less aggressive parameters, (2) Increasing margin of safety in entry/exit rules, (3) Testing with wider slippage assumptions.",
            "Stress Testing": "Improve crisis resilience by: (1) Adding volatility-based position sizing, (2) Implementing crisis detection and reduced exposure, (3) Testing with wider stop-losses during high volatility."
        }

        return remediation_map.get(criterion.criterion, f"Review and adjust {criterion.criterion}")
