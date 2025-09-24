"""
Verify that the refined parameters achieve the overfitting target (<0.3)
"""

def verify_overfitting_target():
    # Universal baseline
    baseline = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

    # Final refined parameters (aggressive regularization v2)
    refined_params_v2 = {
        "Tokyo": {"confidence_threshold": 64.0, "min_risk_reward": 2.6},
        "London": {"confidence_threshold": 61.0, "min_risk_reward": 2.3},
        "New_York": {"confidence_threshold": 59.0, "min_risk_reward": 2.2},
        "Sydney": {"confidence_threshold": 63.0, "min_risk_reward": 2.5},
        "Overlap": {"confidence_threshold": 59.0, "min_risk_reward": 2.2}
    }

    # Original overfitted parameters
    original_params = {
        "Tokyo": {"confidence_threshold": 85.0, "min_risk_reward": 4.0},
        "London": {"confidence_threshold": 72.0, "min_risk_reward": 3.2},
        "New_York": {"confidence_threshold": 70.0, "min_risk_reward": 2.8},
        "Sydney": {"confidence_threshold": 78.0, "min_risk_reward": 3.5},
        "Overlap": {"confidence_threshold": 70.0, "min_risk_reward": 2.8}
    }

    def calc_overfitting_score(params):
        deviations = []
        for session_params in params.values():
            conf_dev = abs(session_params["confidence_threshold"] - baseline["confidence_threshold"]) / 50
            rr_dev = (session_params["min_risk_reward"] - baseline["min_risk_reward"]) / 3
            combined_dev = conf_dev + rr_dev
            deviations.append(combined_dev)

        avg_dev = sum(deviations) / len(deviations)
        max_dev = max(deviations)
        std_dev = (sum((d - avg_dev) ** 2 for d in deviations) / len(deviations)) ** 0.5

        return min(1.0, avg_dev * 0.4 + max_dev * 0.4 + std_dev * 0.2)

    original_score = calc_overfitting_score(original_params)
    refined_score_v2 = calc_overfitting_score(refined_params_v2)
    reduction = (original_score - refined_score_v2) / original_score

    print("OVERFITTING TARGET VERIFICATION")
    print("=" * 45)
    print(f"Original Overfitting Score:     {original_score:.3f} (CRITICAL)")
    print(f"Refined V2 Overfitting Score:   {refined_score_v2:.3f}")
    print(f"Target Achievement (<0.3):      {'✅ SUCCESS' if refined_score_v2 < 0.3 else '❌ FAILED'}")
    print(f"Overfitting Reduction:          {reduction:.1%}")

    print(f"\nDETAILED ANALYSIS:")
    print("-" * 25)

    deviations = []
    for session, params in refined_params_v2.items():
        conf_dev = abs(params["confidence_threshold"] - baseline["confidence_threshold"])
        rr_dev = params["min_risk_reward"] - baseline["min_risk_reward"]
        print(f"{session:8}: Conf deviation: {conf_dev:4.1f}, R:R premium: {rr_dev:3.1f}")

        normalized_dev = conf_dev / 50 + rr_dev / 3
        deviations.append(normalized_dev)

    avg_dev = sum(deviations) / len(deviations)
    max_dev = max(deviations)
    print(f"\nNormalized deviations:")
    print(f"Average: {avg_dev:.3f}, Maximum: {max_dev:.3f}")

    return refined_score_v2 < 0.3

if __name__ == "__main__":
    success = verify_overfitting_target()
    print(f"\n{'=' * 45}")
    print(f"OVERFITTING REDUCTION: {'✅ TARGET ACHIEVED' if success else '❌ TARGET NOT MET'}")