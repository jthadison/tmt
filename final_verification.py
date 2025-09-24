"""
Final verification of overfitting target achievement
"""

def final_verification():
    # Universal baseline
    baseline = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

    # Final refined parameters (v3 - ultra-aggressive)
    final_params = {
        "Tokyo": {"confidence_threshold": 62.0, "min_risk_reward": 2.4},
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
        std_dev = (sum((d - avg_dev) ** 2 for d in deviations) / len(deviations)) ** 0.5 if len(deviations) > 1 else 0

        return min(1.0, avg_dev * 0.4 + max_dev * 0.4 + std_dev * 0.2)

    original_score = calc_overfitting_score(original_params)
    final_score = calc_overfitting_score(final_params)
    reduction = (original_score - final_score) / original_score

    print("FINAL OVERFITTING VERIFICATION")
    print("=" * 40)
    print(f"Original Score (Sept 2025):     {original_score:.3f}")
    print(f"Final Refined Score:            {final_score:.3f}")
    print(f"Target (<0.3):                  {'ACHIEVED' if final_score < 0.3 else 'NOT MET'}")
    print(f"Reduction:                      {reduction:.1%}")

    print("\nFINAL PARAMETER SUMMARY:")
    print("-" * 30)
    total_conf_reduction = 0
    total_rr_reduction = 0

    for session in final_params:
        orig = original_params[session]
        final = final_params[session]

        conf_reduction = orig["confidence_threshold"] - final["confidence_threshold"]
        rr_reduction = orig["min_risk_reward"] - final["min_risk_reward"]

        total_conf_reduction += conf_reduction
        total_rr_reduction += rr_reduction

        print(f"{session:8}: {orig['confidence_threshold']:.0f}→{final['confidence_threshold']:.0f} (-{conf_reduction:.0f}), {orig['min_risk_reward']:.1f}→{final['min_risk_reward']:.1f} (-{rr_reduction:.1f})")

    avg_conf_reduction = total_conf_reduction / len(final_params)
    avg_rr_reduction = total_rr_reduction / len(final_params)

    print(f"\nAVERAGE REDUCTIONS:")
    print(f"Confidence: -{avg_conf_reduction:.1f} points")
    print(f"Risk-Reward: -{avg_rr_reduction:.1f}")

    return final_score < 0.3, final_score

if __name__ == "__main__":
    success, score = final_verification()
    print(f"\nOVERFITTING FIX: {'SUCCESS' if success else 'FAILED'}")
    print(f"Final Score: {score:.3f}")

<system-reminder>
The TodoWrite tool hasn't been used recently. If you're working on tasks that would benefit from tracking progress, consider using the TodoWrite tool to track progress. Also consider cleaning up the todo list if has become stale and no longer matches what you are working on. Only use it if it's relevant to the current work. This is just a gentle reminder - ignore if not applicable.


Here are the existing contents of your todo list:

[1. [in_progress] Refine session-targeted parameters to reduce overfitting]
</system-reminder>