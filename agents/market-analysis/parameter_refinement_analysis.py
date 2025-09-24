"""
Session-Targeted Parameter Refinement Analysis
Addresses overfitting in original session parameters (overfitting score: 0.634 → target: <0.3)
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class ParameterAnalysis:
    """Analysis results for parameter overfitting"""
    session: str
    original_confidence: float
    original_risk_reward: float
    overfitting_factors: List[str]
    recommended_confidence: float
    recommended_risk_reward: float
    regularization_applied: List[str]
    expected_overfitting_reduction: float

class ParameterRefinementEngine:
    """Engine to refine session-targeted parameters and reduce overfitting"""

    def __init__(self):
        # Original session parameters (from September failure analysis)
        self.original_session_parameters = {
            "TOKYO": {"confidence_threshold": 85.0, "min_risk_reward": 4.0},
            "LONDON": {"confidence_threshold": 72.0, "min_risk_reward": 3.2},
            "NEW_YORK": {"confidence_threshold": 70.0, "min_risk_reward": 2.8},
            "SYDNEY": {"confidence_threshold": 78.0, "min_risk_reward": 3.5},
            "OVERLAP": {"confidence_threshold": 70.0, "min_risk_reward": 2.8}
        }

        # Universal Cycle 4 baseline (known stable parameters)
        self.universal_baseline = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

        # Regularization constraints
        self.MAX_DEVIATION_FROM_BASELINE = 15.0  # Max confidence deviation from universal
        self.MAX_RR_PREMIUM = 1.5  # Max R:R premium over universal
        self.MIN_CROSS_SESSION_SIMILARITY = 0.7  # Require similarity between sessions

    def analyze_overfitting_sources(self) -> Dict[str, ParameterAnalysis]:
        """Analyze sources of overfitting in original session parameters"""

        analyses = {}
        baseline_conf = self.universal_baseline["confidence_threshold"]
        baseline_rr = self.universal_baseline["min_risk_reward"]

        for session, params in self.original_session_parameters.items():
            overfitting_factors = []

            # Factor 1: Excessive deviation from universal baseline
            conf_deviation = abs(params["confidence_threshold"] - baseline_conf)
            if conf_deviation > 20:  # More than 20 points from baseline
                overfitting_factors.append(f"Excessive confidence deviation: {conf_deviation:.1f}")

            # Factor 2: Extreme risk-reward requirements
            rr_premium = params["min_risk_reward"] - baseline_rr
            if rr_premium > 2.0:  # More than 2x premium
                overfitting_factors.append(f"Extreme R:R premium: {rr_premium:.1f}")

            # Factor 3: Parameter combinations that are too specific
            if params["confidence_threshold"] > 80 and params["min_risk_reward"] > 3.5:
                overfitting_factors.append("Ultra-selective combination (confidence >80 + R:R >3.5)")

            # Factor 4: Lack of robustness (too narrow parameter space)
            parameter_specificity = (conf_deviation / 50) + (rr_premium / 3)
            if parameter_specificity > 0.6:
                overfitting_factors.append(f"High parameter specificity: {parameter_specificity:.2f}")

            analyses[session] = ParameterAnalysis(
                session=session,
                original_confidence=params["confidence_threshold"],
                original_risk_reward=params["min_risk_reward"],
                overfitting_factors=overfitting_factors,
                recommended_confidence=0,  # Will be calculated
                recommended_risk_reward=0,  # Will be calculated
                regularization_applied=[],  # Will be populated
                expected_overfitting_reduction=0  # Will be calculated
            )

        return analyses

    def apply_regularization_techniques(self, analyses: Dict[str, ParameterAnalysis]) -> Dict[str, ParameterAnalysis]:
        """Apply regularization techniques to reduce overfitting"""

        baseline_conf = self.universal_baseline["confidence_threshold"]
        baseline_rr = self.universal_baseline["min_risk_reward"]

        for session, analysis in analyses.items():
            regularization_applied = []

            # Technique 1: Shrinkage towards universal baseline (L2-like regularization)
            shrinkage_factor = 0.3  # 30% shrinkage towards baseline

            shrunk_confidence = (
                analysis.original_confidence * (1 - shrinkage_factor) +
                baseline_conf * shrinkage_factor
            )
            shrunk_rr = (
                analysis.original_risk_reward * (1 - shrinkage_factor) +
                baseline_rr * shrinkage_factor
            )
            regularization_applied.append(f"Shrinkage regularization (30% towards universal)")

            # Technique 2: Constraint-based bounds (hard limits)
            max_allowed_conf = baseline_conf + self.MAX_DEVIATION_FROM_BASELINE
            max_allowed_rr = baseline_rr + self.MAX_RR_PREMIUM

            constrained_confidence = min(shrunk_confidence, max_allowed_conf)
            constrained_rr = min(shrunk_rr, max_allowed_rr)

            if constrained_confidence < shrunk_confidence:
                regularization_applied.append(f"Confidence bounded to {max_allowed_conf}")
            if constrained_rr < shrunk_rr:
                regularization_applied.append(f"R:R bounded to {max_allowed_rr}")

            # Technique 3: Cross-session consistency enforcement
            all_refined_confidences = []
            all_refined_rrs = []

            # Collect all preliminary refined values
            for other_session, other_analysis in analyses.items():
                if other_session != session:
                    other_shrunk_conf = (
                        other_analysis.original_confidence * (1 - shrinkage_factor) +
                        baseline_conf * shrinkage_factor
                    )
                    other_constrained_conf = min(other_shrunk_conf, max_allowed_conf)
                    all_refined_confidences.append(other_constrained_conf)

                    other_shrunk_rr = (
                        other_analysis.original_risk_reward * (1 - shrinkage_factor) +
                        baseline_rr * shrinkage_factor
                    )
                    other_constrained_rr = min(other_shrunk_rr, max_allowed_rr)
                    all_refined_rrs.append(other_constrained_rr)

            # Apply consistency constraint (don't deviate too much from session average)
            if all_refined_confidences:
                session_avg_conf = np.mean(all_refined_confidences + [constrained_confidence])
                max_deviation_from_avg = 8.0  # Max 8 points from session average

                if abs(constrained_confidence - session_avg_conf) > max_deviation_from_avg:
                    if constrained_confidence > session_avg_conf:
                        constrained_confidence = session_avg_conf + max_deviation_from_avg
                    else:
                        constrained_confidence = session_avg_conf - max_deviation_from_avg
                    regularization_applied.append("Cross-session consistency applied")

            # Technique 4: Minimum effective difference (avoid over-optimization)
            min_effective_diff = 3.0  # Must be at least 3 points different from universal
            if abs(constrained_confidence - baseline_conf) < min_effective_diff:
                # If too close to universal, just use universal + small buffer
                if constrained_confidence > baseline_conf:
                    constrained_confidence = baseline_conf + min_effective_diff
                else:
                    constrained_confidence = baseline_conf - min_effective_diff
                regularization_applied.append("Minimum effective difference enforced")

            # Calculate expected overfitting reduction
            original_specificity = (
                abs(analysis.original_confidence - baseline_conf) / 50 +
                (analysis.original_risk_reward - baseline_rr) / 3
            )
            refined_specificity = (
                abs(constrained_confidence - baseline_conf) / 50 +
                (constrained_rr - baseline_rr) / 3
            )
            overfitting_reduction = max(0, (original_specificity - refined_specificity) / original_specificity)

            # Update analysis with refined parameters
            analysis.recommended_confidence = constrained_confidence
            analysis.recommended_risk_reward = constrained_rr
            analysis.regularization_applied = regularization_applied
            analysis.expected_overfitting_reduction = overfitting_reduction

        return analyses

    def generate_refined_session_parameters(self) -> Tuple[Dict, Dict]:
        """Generate refined session parameters with reduced overfitting"""

        # Step 1: Analyze overfitting sources
        analyses = self.analyze_overfitting_sources()

        # Step 2: Apply regularization
        refined_analyses = self.apply_regularization_techniques(analyses)

        # Step 3: Generate refined parameters
        refined_parameters = {}
        analysis_summary = {}

        session_mapping = {
            "TOKYO": "Tokyo",
            "LONDON": "London",
            "NEW_YORK": "New_York",
            "SYDNEY": "Sydney",
            "OVERLAP": "Overlap"
        }

        for session, analysis in refined_analyses.items():
            # Round to practical values
            refined_conf = round(analysis.recommended_confidence, 1)
            refined_rr = round(analysis.recommended_risk_reward, 1)

            session_key = session_mapping[session]

            refined_parameters[session_key] = {
                "confidence_threshold": refined_conf,
                "min_risk_reward": refined_rr,
                "max_risk_reward": refined_rr * 1.4,  # Add upper bound
                "position_size_multiplier": 1.0,  # Standard sizing
                "volatility_adjustment_enabled": True,
                "source": "refined_overfitting_reduction_v1",
                "refinement_date": "2025-09-23",
                "original_confidence": analysis.original_confidence,
                "original_risk_reward": analysis.original_risk_reward,
                "overfitting_reduction": f"{analysis.expected_overfitting_reduction:.1%}"
            }

            analysis_summary[session] = {
                "original": {
                    "confidence": analysis.original_confidence,
                    "risk_reward": analysis.original_risk_reward
                },
                "refined": {
                    "confidence": refined_conf,
                    "risk_reward": refined_rr
                },
                "changes": {
                    "confidence_change": refined_conf - analysis.original_confidence,
                    "rr_change": refined_rr - analysis.original_risk_reward
                },
                "overfitting_factors": analysis.overfitting_factors,
                "regularization_applied": analysis.regularization_applied,
                "expected_overfitting_reduction": analysis.expected_overfitting_reduction
            }

        return refined_parameters, analysis_summary

    def validate_overfitting_reduction(self, original_params: Dict, refined_params: Dict) -> Dict:
        """Validate that refined parameters actually reduce overfitting"""

        baseline_conf = self.universal_baseline["confidence_threshold"]
        baseline_rr = self.universal_baseline["min_risk_reward"]

        # Calculate original overfitting score
        original_deviations = []
        for session_params in original_params.values():
            conf_dev = abs(session_params["confidence_threshold"] - baseline_conf) / 50
            rr_dev = (session_params["min_risk_reward"] - baseline_rr) / 3
            combined_dev = conf_dev + rr_dev
            original_deviations.append(combined_dev)

        original_avg_deviation = np.mean(original_deviations)
        original_max_deviation = np.max(original_deviations)
        original_std_deviation = np.std(original_deviations)

        # Calculate refined overfitting score
        refined_deviations = []
        for session_params in refined_params.values():
            conf_dev = abs(session_params["confidence_threshold"] - baseline_conf) / 50
            rr_dev = (session_params["min_risk_reward"] - baseline_rr) / 3
            combined_dev = conf_dev + rr_dev
            refined_deviations.append(combined_dev)

        refined_avg_deviation = np.mean(refined_deviations)
        refined_max_deviation = np.max(refined_deviations)
        refined_std_deviation = np.std(refined_deviations)

        # Overfitting score (0 = no overfitting, 1 = extreme overfitting)
        original_overfitting_score = min(1.0, (original_avg_deviation * 0.4 +
                                             original_max_deviation * 0.4 +
                                             original_std_deviation * 0.2))

        refined_overfitting_score = min(1.0, (refined_avg_deviation * 0.4 +
                                            refined_max_deviation * 0.4 +
                                            refined_std_deviation * 0.2))

        overfitting_improvement = (original_overfitting_score - refined_overfitting_score) / original_overfitting_score

        return {
            "original_overfitting_score": original_overfitting_score,
            "refined_overfitting_score": refined_overfitting_score,
            "overfitting_reduction": overfitting_improvement,
            "meets_target": refined_overfitting_score < 0.3,
            "original_stats": {
                "avg_deviation": original_avg_deviation,
                "max_deviation": original_max_deviation,
                "std_deviation": original_std_deviation
            },
            "refined_stats": {
                "avg_deviation": refined_avg_deviation,
                "max_deviation": refined_max_deviation,
                "std_deviation": refined_std_deviation
            }
        }

def run_parameter_refinement_analysis():
    """Run complete parameter refinement analysis"""

    print("🔧 Session-Targeted Parameter Refinement Analysis")
    print("=" * 60)

    engine = ParameterRefinementEngine()

    # Generate refined parameters
    refined_params, analysis_summary = engine.generate_refined_session_parameters()

    print("\n📊 OVERFITTING ANALYSIS BY SESSION:")
    print("-" * 40)

    for session, analysis in analysis_summary.items():
        print(f"\n{session.upper()} SESSION:")
        print(f"  Original: Confidence {analysis['original']['confidence']:.1f}%, R:R {analysis['original']['risk_reward']:.1f}")
        print(f"  Refined:  Confidence {analysis['refined']['confidence']:.1f}%, R:R {analysis['refined']['risk_reward']:.1f}")
        print(f"  Changes:  Confidence {analysis['changes']['confidence_change']:+.1f}, R:R {analysis['changes']['rr_change']:+.1f}")
        print(f"  Overfitting Reduction: {analysis['expected_overfitting_reduction']:.1%}")

        if analysis['overfitting_factors']:
            print(f"  Issues Found: {len(analysis['overfitting_factors'])}")
            for factor in analysis['overfitting_factors']:
                print(f"    • {factor}")

    # Validate overfitting reduction
    validation = engine.validate_overfitting_reduction(
        engine.original_session_parameters,
        {k: v for k, v in refined_params.items()}
    )

    print(f"\n🎯 OVERFITTING VALIDATION:")
    print("-" * 30)
    print(f"Original Overfitting Score: {validation['original_overfitting_score']:.3f}")
    print(f"Refined Overfitting Score:  {validation['refined_overfitting_score']:.3f}")
    print(f"Overfitting Reduction:      {validation['overfitting_reduction']:.1%}")
    print(f"Meets Target (<0.3):        {'✅ YES' if validation['meets_target'] else '❌ NO'}")

    print(f"\n📈 REFINED SESSION PARAMETERS:")
    print("-" * 35)

    for session, params in refined_params.items():
        print(f"\n{session.upper()}:")
        print(f"  confidence_threshold: {params['confidence_threshold']}")
        print(f"  min_risk_reward: {params['min_risk_reward']}")
        print(f"  max_risk_reward: {params['max_risk_reward']}")
        print(f"  overfitting_reduction: {params['overfitting_reduction']}")

    return refined_params, analysis_summary, validation

if __name__ == "__main__":
    refined_params, analysis, validation = run_parameter_refinement_analysis()