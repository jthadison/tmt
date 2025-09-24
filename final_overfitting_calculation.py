"""
Calculate final overfitting score for the refined parameters to verify target achievement
"""

def calculate_final_overfitting():
    # Universal baseline
    baseline = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

    # Final refined parameters (more aggressive regularization)
    refined_params = {
        "Tokyo": {"confidence_threshold": 67.0, "min_risk_reward": 2.8},
        "London": {"confidence_threshold": 64.0, "min_risk_reward": 2.6},
        "New_York": {"confidence_threshold": 62.0, "min_risk_reward": 2.4},
        "Sydney": {"confidence_threshold": 66.0, "min_risk_reward": 2.7},
        "Overlap": {"confidence_threshold": 62.0, "min_risk_reward": 2.4}
    }

    # Original overfitted parameters for comparison
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
    refined_score = calc_overfitting_score(refined_params)
    reduction = (original_score - refined_score) / original_score

    print("FINAL OVERFITTING CALCULATION")
    print("=" * 40)
    print(f"Original Overfitting Score: {original_score:.3f}")
    print(f"Refined Overfitting Score:  {refined_score:.3f}")
    print(f"Overfitting Reduction:      {reduction:.1%}")
    print(f"Target (<0.3) Achieved:     {'YES' if refined_score < 0.3 else 'NO'}")

    print("\nPARAMETER CHANGES:")
    print("-" * 20)
    for session in original_params:
        orig_conf = original_params[session]["confidence_threshold"]
        orig_rr = original_params[session]["min_risk_reward"]
        refined_conf = refined_params[session]["confidence_threshold"]
        refined_rr = refined_params[session]["min_risk_reward"]

        conf_change = refined_conf - orig_conf
        rr_change = refined_rr - orig_rr

        print(f"{session:8}: Conf {orig_conf:5.1f} -> {refined_conf:5.1f} ({conf_change:+.1f}), R:R {orig_rr:.1f} -> {refined_rr:.1f} ({rr_change:+.1f})")

    return refined_score < 0.3

if __name__ == "__main__":
    success = calculate_final_overfitting()