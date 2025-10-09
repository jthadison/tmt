"""
Acceptance Criteria Validators - Story 11.3, Task 10

Validates walk-forward results against acceptance criteria:
- Out-of-sample Sharpe ratio thresholds
- Overfitting score limits
- Max drawdown constraints
- Win rate stability
"""

import numpy as np
from typing import List, Dict, Any
import logging

from .models import WindowResult

logger = logging.getLogger(__name__)


class AcceptanceCriteriaValidator:
    """
    Validates walk-forward results against acceptance criteria

    Acceptance criteria from Story 11.3:
    - ✅ Avg out-of-sample Sharpe > 1.0
    - ✅ Out-of-sample Sharpe > 70% of in-sample Sharpe (overfitting score < 0.3)
    - ✅ Max drawdown in testing < 20%
    - ✅ Win rate stability variance < 10%

    Rejection criteria:
    - ❌ Out-of-sample Sharpe < 0.5
    - ❌ Out-of-sample Sharpe < 50% of in-sample Sharpe (overfitting score > 0.5)
    - ❌ Any testing period has max drawdown > 30%
    """

    def __init__(
        self,
        min_oos_sharpe: float = 1.0,
        min_oos_sharpe_ratio: float = 0.7,  # OOS must be 70% of IS
        max_overfitting_score: float = 0.3,
        max_drawdown_pct: float = 20.0,
        max_win_rate_variance: float = 0.1,  # 10% variance
        reject_oos_sharpe: float = 0.5,
        reject_overfitting_score: float = 0.5,
        reject_drawdown_pct: float = 30.0
    ):
        """
        Initialize acceptance criteria validator

        Args:
            min_oos_sharpe: Minimum average out-of-sample Sharpe ratio
            min_oos_sharpe_ratio: Minimum OOS/IS Sharpe ratio (0.7 = 70%)
            max_overfitting_score: Maximum acceptable overfitting score
            max_drawdown_pct: Maximum testing drawdown percentage
            max_win_rate_variance: Maximum win rate variance across windows
            reject_oos_sharpe: Hard rejection threshold for OOS Sharpe
            reject_overfitting_score: Hard rejection threshold for overfitting
            reject_drawdown_pct: Hard rejection threshold for drawdown
        """
        self.min_oos_sharpe = min_oos_sharpe
        self.min_oos_sharpe_ratio = min_oos_sharpe_ratio
        self.max_overfitting_score = max_overfitting_score
        self.max_drawdown_pct = max_drawdown_pct
        self.max_win_rate_variance = max_win_rate_variance
        self.reject_oos_sharpe = reject_oos_sharpe
        self.reject_overfitting_score = reject_overfitting_score
        self.reject_drawdown_pct = reject_drawdown_pct

    def validate(
        self,
        windows: List[WindowResult],
        avg_overfitting_score: float
    ) -> Dict[str, Any]:
        """
        Validate walk-forward results against all acceptance criteria

        Args:
            windows: List of walk-forward window results
            avg_overfitting_score: Average overfitting score

        Returns:
            Dict containing:
            - status: "PASS" or "FAIL"
            - details: Dict of individual criterion results (True/False)
            - messages: List of human-readable messages
        """

        details = {}
        messages = []

        # Calculate aggregate metrics
        avg_oos_sharpe = np.mean([w.out_of_sample_sharpe for w in windows])
        oos_drawdowns = [w.out_of_sample_drawdown for w in windows]
        max_oos_drawdown = max(abs(dd) for dd in oos_drawdowns)
        oos_win_rates = [w.out_of_sample_win_rate for w in windows]
        win_rate_variance = np.var(oos_win_rates) if len(oos_win_rates) > 1 else 0.0

        # Check 1: Avg out-of-sample Sharpe > minimum
        check_oos_sharpe = avg_oos_sharpe >= self.min_oos_sharpe
        details['oos_sharpe_acceptable'] = check_oos_sharpe

        if check_oos_sharpe:
            messages.append(
                f"✅ Avg OOS Sharpe ratio ({avg_oos_sharpe:.2f}) >= {self.min_oos_sharpe}"
            )
        else:
            messages.append(
                f"❌ Avg OOS Sharpe ratio ({avg_oos_sharpe:.2f}) < {self.min_oos_sharpe}"
            )

        # Check 2: Hard rejection - OOS Sharpe too low
        check_oos_sharpe_not_rejected = avg_oos_sharpe >= self.reject_oos_sharpe
        details['oos_sharpe_not_rejected'] = check_oos_sharpe_not_rejected

        if not check_oos_sharpe_not_rejected:
            messages.append(
                f"❌ REJECTION: Avg OOS Sharpe ratio ({avg_oos_sharpe:.2f}) "
                f"< rejection threshold ({self.reject_oos_sharpe})"
            )

        # Check 3: Overfitting score acceptable
        check_overfitting = avg_overfitting_score <= self.max_overfitting_score
        details['overfitting_acceptable'] = check_overfitting

        if check_overfitting:
            messages.append(
                f"✅ Avg overfitting score ({avg_overfitting_score:.3f}) "
                f"<= {self.max_overfitting_score}"
            )
        else:
            messages.append(
                f"❌ Avg overfitting score ({avg_overfitting_score:.3f}) "
                f"> {self.max_overfitting_score}"
            )

        # Check 4: Hard rejection - overfitting too severe
        check_overfitting_not_rejected = avg_overfitting_score <= self.reject_overfitting_score
        details['overfitting_not_rejected'] = check_overfitting_not_rejected

        if not check_overfitting_not_rejected:
            messages.append(
                f"❌ REJECTION: Avg overfitting score ({avg_overfitting_score:.3f}) "
                f"> rejection threshold ({self.reject_overfitting_score})"
            )

        # Check 5: OOS Sharpe ratio (vs in-sample)
        check_oos_ratio = True
        for window in windows:
            if window.in_sample_sharpe > 0:
                ratio = window.out_of_sample_sharpe / window.in_sample_sharpe
                if ratio < self.min_oos_sharpe_ratio:
                    check_oos_ratio = False
                    messages.append(
                        f"❌ Window {window.window_index}: OOS/IS ratio "
                        f"({ratio:.2f}) < {self.min_oos_sharpe_ratio}"
                    )
                    break

        details['oos_is_ratio_acceptable'] = check_oos_ratio

        if check_oos_ratio:
            messages.append(
                f"✅ All windows have OOS/IS Sharpe ratio >= {self.min_oos_sharpe_ratio}"
            )

        # Check 6: Max drawdown in testing
        check_drawdown = max_oos_drawdown <= self.max_drawdown_pct
        details['drawdown_acceptable'] = check_drawdown

        if check_drawdown:
            messages.append(
                f"✅ Max OOS drawdown ({max_oos_drawdown:.1f}%) "
                f"<= {self.max_drawdown_pct}%"
            )
        else:
            messages.append(
                f"❌ Max OOS drawdown ({max_oos_drawdown:.1f}%) "
                f"> {self.max_drawdown_pct}%"
            )

        # Check 7: Hard rejection - drawdown too severe
        check_drawdown_not_rejected = max_oos_drawdown <= self.reject_drawdown_pct
        details['drawdown_not_rejected'] = check_drawdown_not_rejected

        if not check_drawdown_not_rejected:
            messages.append(
                f"❌ REJECTION: Max OOS drawdown ({max_oos_drawdown:.1f}%) "
                f"> rejection threshold ({self.reject_drawdown_pct}%)"
            )

        # Check 8: Win rate stability
        check_win_rate_stability = win_rate_variance <= self.max_win_rate_variance
        details['win_rate_stable'] = check_win_rate_stability

        if check_win_rate_stability:
            messages.append(
                f"✅ Win rate variance ({win_rate_variance:.3f}) "
                f"<= {self.max_win_rate_variance}"
            )
        else:
            messages.append(
                f"❌ Win rate variance ({win_rate_variance:.3f}) "
                f"> {self.max_win_rate_variance}"
            )

        # Overall status
        # Hard rejections
        hard_rejections = [
            check_oos_sharpe_not_rejected,
            check_overfitting_not_rejected,
            check_drawdown_not_rejected
        ]

        # Soft criteria
        soft_criteria = [
            check_oos_sharpe,
            check_overfitting,
            check_oos_ratio,
            check_drawdown,
            check_win_rate_stability
        ]

        # Fail if any hard rejection OR majority of soft criteria fail
        if not all(hard_rejections):
            status = "FAIL"
            messages.insert(0, "❌ VALIDATION FAILED: Hard rejection criteria violated")
        elif sum(soft_criteria) < len(soft_criteria) * 0.6:  # 60% threshold
            status = "FAIL"
            messages.insert(0, "❌ VALIDATION FAILED: Too many acceptance criteria failed")
        else:
            status = "PASS"
            messages.insert(0, "✅ VALIDATION PASSED: All acceptance criteria met")

        logger.info(f"Validation result: {status}")
        for msg in messages:
            logger.info(f"  {msg}")

        return {
            'status': status,
            'details': details,
            'messages': messages
        }

    def validate_individual_window(
        self,
        window: WindowResult
    ) -> Dict[str, Any]:
        """
        Validate a single window against criteria

        Args:
            window: Window result to validate

        Returns:
            Dict with validation results for this window
        """

        details = {}
        messages = []

        # Check OOS Sharpe
        details['oos_sharpe_ok'] = window.out_of_sample_sharpe >= self.reject_oos_sharpe

        # Check overfitting
        details['overfitting_ok'] = window.overfitting_score <= self.reject_overfitting_score

        # Check drawdown
        details['drawdown_ok'] = abs(window.out_of_sample_drawdown) <= self.reject_drawdown_pct

        # Check OOS/IS ratio
        if window.in_sample_sharpe > 0:
            ratio = window.out_of_sample_sharpe / window.in_sample_sharpe
            details['oos_is_ratio_ok'] = ratio >= self.min_oos_sharpe_ratio
        else:
            details['oos_is_ratio_ok'] = False

        # Overall window status
        all_checks = all(details.values())
        details['window_valid'] = all_checks

        if all_checks:
            messages.append(f"Window {window.window_index}: PASS")
        else:
            messages.append(f"Window {window.window_index}: FAIL")
            if not details['oos_sharpe_ok']:
                messages.append(
                    f"  - OOS Sharpe ({window.out_of_sample_sharpe:.2f}) too low"
                )
            if not details['overfitting_ok']:
                messages.append(
                    f"  - Overfitting score ({window.overfitting_score:.3f}) too high"
                )
            if not details['drawdown_ok']:
                messages.append(
                    f"  - Drawdown ({window.out_of_sample_drawdown:.1f}%) too high"
                )
            if not details['oos_is_ratio_ok']:
                messages.append(
                    f"  - OOS/IS ratio too low"
                )

        return {
            'details': details,
            'messages': messages
        }
