"""
Manual calculation of refined session parameters to reduce overfitting
Based on regularization analysis from September 2025 degradation
"""

def calculate_refined_parameters():
    """Calculate refined session parameters using regularization techniques"""

    # Original parameters that caused overfitting (score: 0.634)
    original_params = {
        "TOKYO": {"confidence_threshold": 85.0, "min_risk_reward": 4.0},
        "LONDON": {"confidence_threshold": 72.0, "min_risk_reward": 3.2},
        "NEW_YORK": {"confidence_threshold": 70.0, "min_risk_reward": 2.8},
        "SYDNEY": {"confidence_threshold": 78.0, "min_risk_reward": 3.5},
        "OVERLAP": {"confidence_threshold": 70.0, "min_risk_reward": 2.8}
    }

    # Universal baseline (known stable)
    universal_baseline = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

    print("ORIGINAL SESSION PARAMETERS (Overfitting Score: 0.634)")
    print("=" * 60)
    for session, params in original_params.items():
        deviation = abs(params["confidence_threshold"] - universal_baseline["confidence_threshold"])
        rr_premium = params["min_risk_reward"] - universal_baseline["min_risk_reward"]
        print(f"{session:8}: Confidence {params['confidence_threshold']:5.1f}% (+{deviation:4.1f}), R:R {params['min_risk_reward']:3.1f} (+{rr_premium:.1f})")

    # Apply regularization techniques
    refined_params = {}
    session_mapping = {
        "TOKYO": "Tokyo",
        "LONDON": "London",
        "NEW_YORK": "New_York",
        "SYDNEY": "Sydney",
        "OVERLAP": "Overlap"
    }

    print("\nREGULARIZATION PROCESS:")
    print("-" * 30)

    for session, original in original_params.items():
        print(f"\n{session} SESSION:")

        # Step 1: Shrinkage towards universal (30% shrinkage)
        shrinkage_factor = 0.3
        shrunk_conf = (original["confidence_threshold"] * 0.7 +
                      universal_baseline["confidence_threshold"] * 0.3)
        shrunk_rr = (original["min_risk_reward"] * 0.7 +
                    universal_baseline["min_risk_reward"] * 0.3)

        print(f"  Step 1 - Shrinkage (30%): Conf {shrunk_conf:.1f}, R:R {shrunk_rr:.1f}")

        # Step 2: Hard constraints (max deviation from universal)
        max_conf_deviation = 15.0
        max_rr_premium = 1.5

        max_allowed_conf = universal_baseline["confidence_threshold"] + max_conf_deviation
        max_allowed_rr = universal_baseline["min_risk_reward"] + max_rr_premium

        constrained_conf = min(shrunk_conf, max_allowed_conf)
        constrained_rr = min(shrunk_rr, max_allowed_rr)

        print(f"  Step 2 - Constraints:      Conf {constrained_conf:.1f}, R:R {constrained_rr:.1f}")

        # Step 3: Cross-session consistency (don't deviate too much from session average)
        # For simplicity, apply a moderate adjustment
        if constrained_conf > 75:  # If still too high
            constrained_conf = 75.0
        if constrained_rr > 3.0:   # If still too high
            constrained_rr = 3.0

        # Step 4: Round to practical values
        final_conf = round(constrained_conf, 1)
        final_rr = round(constrained_rr, 1)

        print(f"  Final Refined:             Conf {final_conf:.1f}, R:R {final_rr:.1f}")

        # Calculate changes
        conf_change = final_conf - original["confidence_threshold"]
        rr_change = final_rr - original["min_risk_reward"]
        print(f"  Changes:                   Conf {conf_change:+.1f}, R:R {rr_change:+.1f}")

        session_key = session_mapping[session]
        refined_params[session_key] = {
            "confidence_threshold": final_conf,
            "min_risk_reward": final_rr,
            "max_risk_reward": final_rr * 1.4,
            "source": "refined_overfitting_reduction_v1"
        }

    # Calculate overfitting scores
    def calculate_overfitting_score(params, baseline):
        deviations = []
        for session_params in params.values():
            if isinstance(session_params, dict) and "confidence_threshold" in session_params:
                conf_dev = abs(session_params["confidence_threshold"] - baseline["confidence_threshold"]) / 50
                rr_dev = (session_params["min_risk_reward"] - baseline["min_risk_reward"]) / 3
                combined_dev = conf_dev + rr_dev
                deviations.append(combined_dev)

        if not deviations:
            return 0

        avg_dev = sum(deviations) / len(deviations)
        max_dev = max(deviations)
        std_dev = (sum((d - avg_dev) ** 2 for d in deviations) / len(deviations)) ** 0.5

        return min(1.0, avg_dev * 0.4 + max_dev * 0.4 + std_dev * 0.2)

    original_overfitting = calculate_overfitting_score(original_params, universal_baseline)
    refined_overfitting = calculate_overfitting_score(refined_params, universal_baseline)

    overfitting_reduction = (original_overfitting - refined_overfitting) / original_overfitting if original_overfitting > 0 else 0

    print("\n" + "=" * 60)
    print("OVERFITTING ANALYSIS RESULTS:")
    print("-" * 30)
    print(f"Original Overfitting Score: {original_overfitting:.3f}")
    print(f"Refined Overfitting Score:  {refined_overfitting:.3f}")
    print(f"Overfitting Reduction:      {overfitting_reduction:.1%}")
    print(f"Target Achievement (<0.3):  {'YES' if refined_overfitting < 0.3 else 'NO'}")

    print("\nREFINED SESSION PARAMETERS:")
    print("-" * 35)

    for session, params in refined_params.items():
        print(f"\n{session.upper()}:")
        print(f"  confidence_threshold: {params['confidence_threshold']}")
        print(f"  min_risk_reward: {params['min_risk_reward']}")
        print(f"  max_risk_reward: {params['max_risk_reward']}")

    return refined_params, {
        "original_overfitting_score": original_overfitting,
        "refined_overfitting_score": refined_overfitting,
        "overfitting_reduction": overfitting_reduction,
        "meets_target": refined_overfitting < 0.3
    }

if __name__ == "__main__":
    refined_params, validation = calculate_refined_parameters()