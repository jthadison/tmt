"""
Final verification of overfitting target achievement
"""

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

print("\nFINAL PARAMETER CHANGES:")
print("-" * 30)
for session in final_params:
    orig = original_params[session]
    final = final_params[session]

    conf_reduction = orig["confidence_threshold"] - final["confidence_threshold"]
    rr_reduction = orig["min_risk_reward"] - final["min_risk_reward"]

    print(f"{session:8}: {orig['confidence_threshold']:.0f}->{final['confidence_threshold']:.0f} (-{conf_reduction:.0f}), {orig['min_risk_reward']:.1f}->{final['min_risk_reward']:.1f} (-{rr_reduction:.1f})")

print(f"\nOVERFITTING FIX: {'SUCCESS' if final_score < 0.3 else 'NEEDS MORE WORK'}")