"""
Generate refined session parameters to reduce overfitting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.market_analysis.parameter_refinement_analysis import ParameterRefinementEngine

def main():
    print("Session-Targeted Parameter Refinement Analysis")
    print("=" * 60)

    engine = ParameterRefinementEngine()
    refined_params, analysis_summary = engine.generate_refined_session_parameters()

    print("\nOVERFITTING ANALYSIS BY SESSION:")
    print("-" * 40)

    for session, analysis in analysis_summary.items():
        print(f"\n{session} SESSION:")
        print(f"  Original: Confidence {analysis['original']['confidence']:.1f}%, R:R {analysis['original']['risk_reward']:.1f}")
        print(f"  Refined:  Confidence {analysis['refined']['confidence']:.1f}%, R:R {analysis['refined']['risk_reward']:.1f}")
        print(f"  Changes:  Confidence {analysis['changes']['confidence_change']:+.1f}, R:R {analysis['changes']['rr_change']:+.1f}")

    # Validate overfitting reduction
    validation = engine.validate_overfitting_reduction(
        engine.original_session_parameters,
        {k: v for k, v in refined_params.items()}
    )

    print(f"\nOVERFITTING VALIDATION:")
    print("-" * 30)
    print(f"Original Overfitting Score: {validation['original_overfitting_score']:.3f}")
    print(f"Refined Overfitting Score:  {validation['refined_overfitting_score']:.3f}")
    print(f"Overfitting Reduction:      {validation['overfitting_reduction']:.1%}")
    print(f"Meets Target (<0.3):        {'YES' if validation['meets_target'] else 'NO'}")

    print(f"\nREFINED SESSION PARAMETERS:")
    print("-" * 35)

    for session, params in refined_params.items():
        print(f"\n{session}:")
        print(f"  confidence_threshold: {params['confidence_threshold']}")
        print(f"  min_risk_reward: {params['min_risk_reward']}")
        print(f"  max_risk_reward: {params['max_risk_reward']}")

    return refined_params, validation

if __name__ == "__main__":
    refined_params, validation = main()