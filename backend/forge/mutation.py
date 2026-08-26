"""
VeriTrace — Forge Mutation Engine
Member 3: Adversarial Engine

Receives Sentinel detection feedback and mutates Forge parameters
so the next synthetic identity is harder to detect.

Mutation strategies are keyed to detection reasons:
  - high_smoothness    → inject spend noise to break linearity
  - high_monotonicity  → introduce spending dips/reversals
  - high_regularity    → randomise login variance
  - low_variance       → add human-like volatility
  - fraud_strike       → delay/obscure the bust-out week
  - graph_similarity   → shift base-spend offset so vectors diverge
"""

import random
import numpy as np
from typing import Dict, Any, Optional


# ─── Default Forge parameter profile ────────────────────────────────────────

DEFAULT_PARAMS: Dict[str, Any] = {
    "noise_factor": 0.035,          # Gaussian noise on spend (fraction of base)
    "dip_probability": 0.04,        # Chance of a spend dip week
    "dip_magnitude": 0.15,          # How deep a dip goes (fraction)
    "login_jitter": 1,              # ±jitter on logins per week
    "ramp_rate_variance": 0.05,     # Fraction of ramp_rate used as std dev
    "strike_week_offset": 0,        # Weeks by which bust-out is shifted earlier
    "base_spend_offset": 0.0,       # Added to base_spend to diverge similarity
    "surge_multiplier_cap": 20.0,   # Maximum bust-out surge (reduce to lower anomaly score)
    "stealth_level": 1,             # 1 = easy, 2 = medium, 3 = hard/adaptive
}


def mutate_params(
    current_params: Dict[str, Any],
    detection_features: Dict[str, float],
    was_detected: bool,
    round_number: int,
) -> Dict[str, Any]:
    """
    Given the current Forge parameters and Sentinel's detection features,
    return mutated parameters for the next round.

    Mutation rules:
      - If NOT detected → barely change (small random noise to avoid overfitting)
      - If detected → apply targeted countermeasures to each flagged signal

    Parameters
    ----------
    current_params : dict
        The parameter dict used to generate the last attack.
    detection_features : dict
        The feature scores returned by Sentinel's trajectory model.
        Keys: spend_smoothness, spend_monotonicity, login_regularity, variance_score
    was_detected : bool
        Whether the last attack was flagged by Sentinel.
    round_number : int
        Current adversarial round (1-indexed).

    Returns
    -------
    dict
        New parameter dict for the next round.
    """
    params = current_params.copy()

    if not was_detected:
        # Tiny random perturbation to keep attacking
        params["noise_factor"] = float(np.clip(
            params["noise_factor"] + random.uniform(-0.005, 0.005), 0.01, 0.30
        ))
        params["stealth_level"] = min(3, params["stealth_level"])
        return params

    # ── Detected: apply countermeasures ──────────────────────────────────────

    smoothness = detection_features.get("spend_smoothness", 0.0)
    monotonicity = detection_features.get("spend_monotonicity", 0.0)
    regularity = detection_features.get("login_regularity", 0.0)
    variance = detection_features.get("variance_score", 0.5)

    mutation_log = []

    # 1. Break spend linearity (R² too high)
    if smoothness > 0.75:
        boost = random.uniform(0.04, 0.10)
        params["noise_factor"] = float(np.clip(params["noise_factor"] + boost, 0.01, 0.35))
        # Also introduce spending dips
        params["dip_probability"] = float(np.clip(
            params.get("dip_probability", 0.04) + random.uniform(0.05, 0.15), 0.0, 0.40
        ))
        params["dip_magnitude"] = float(np.clip(
            params.get("dip_magnitude", 0.15) + random.uniform(0.05, 0.15), 0.05, 0.45
        ))
        mutation_log.append("spend_linearity_broken")

    # 2. Break monotonicity (too many non-decreasing weeks)
    if monotonicity > 0.80:
        params["ramp_rate_variance"] = float(np.clip(
            params.get("ramp_rate_variance", 0.05) + random.uniform(0.05, 0.15), 0.01, 0.40
        ))
        params["dip_probability"] = float(np.clip(
            params.get("dip_probability", 0.04) + random.uniform(0.04, 0.12), 0.0, 0.40
        ))
        mutation_log.append("monotonicity_broken")

    # 3. Randomise login timing (too regular)
    if regularity > 0.70:
        params["login_jitter"] = int(np.clip(
            params.get("login_jitter", 1) + random.randint(1, 3), 1, 6
        ))
        mutation_log.append("login_regularity_broken")

    # 4. Add organic spend variance (CV too low)
    if variance < 0.20:
        params["noise_factor"] = float(np.clip(
            params["noise_factor"] + random.uniform(0.03, 0.08), 0.01, 0.35
        ))
        mutation_log.append("variance_boosted")

    # 5. Reduce bust-out size if transaction_anomaly is too high.
    #    Floor at 3.5x — below that the attack isn't a meaningful "bust-out"
    #    and Sentinel can still catch it via trajectory alone.
    bust_out_ratio = detection_features.get("bust_out_ratio", 0.0)
    if bust_out_ratio > 0.50:
        current_cap = params.get("surge_multiplier_cap", 20.0)
        reduction = random.uniform(2.5, 5.0) if bust_out_ratio > 0.70 else random.uniform(1.0, 3.0)
        params["surge_multiplier_cap"] = float(max(3.5, current_cap - reduction))
        mutation_log.append(f"surge_cap_reduced_to_{params['surge_multiplier_cap']:.1f}x")
    elif bust_out_ratio > 0.30:
        current_cap = params.get("surge_multiplier_cap", 20.0)
        params["surge_multiplier_cap"] = float(max(3.5, current_cap - random.uniform(0.5, 1.5)))
        mutation_log.append(f"surge_cap_reduced_to_{params['surge_multiplier_cap']:.1f}x")

    # 6. Shift bust-out timing to be less predictable at week 24
    #    (only start delaying after round 3 to keep the demo clear)
    if round_number >= 3 and params.get("strike_week_offset", 0) == 0:
        params["strike_week_offset"] = random.randint(-2, 2)
        mutation_log.append("strike_week_shifted")

    # 7. Offset base-spend to diverge from known fraud clusters
    if round_number >= 4:
        params["base_spend_offset"] = float(
            params.get("base_spend_offset", 0.0) + random.uniform(-30.0, 30.0)
        )
        mutation_log.append("base_spend_offset_shifted")

    # Escalate stealth level over rounds
    params["stealth_level"] = min(3, max(1, round_number // 3 + 1))
    params["_mutation_log"] = mutation_log

    return params


def params_to_generator_kwargs(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a Forge parameter dict into keyword arguments
    accepted by generate_timeline_adversarial().
    """
    return {
        "noise_factor": params.get("noise_factor", 0.035),
        "dip_probability": params.get("dip_probability", 0.04),
        "dip_magnitude": params.get("dip_magnitude", 0.15),
        "login_jitter": params.get("login_jitter", 1),
        "ramp_rate_variance": params.get("ramp_rate_variance", 0.05),
        "strike_week_offset": params.get("strike_week_offset", 0),
        "base_spend_offset": params.get("base_spend_offset", 0.0),
        "surge_multiplier_cap": params.get("surge_multiplier_cap", 20.0),
    }


def describe_mutation(old_params: Dict[str, Any], new_params: Dict[str, Any]) -> str:
    """Returns a human-readable summary of what changed between rounds."""
    changes = []

    noise_delta = new_params["noise_factor"] - old_params.get("noise_factor", 0.035)
    if abs(noise_delta) > 0.005:
        direction = "increased" if noise_delta > 0 else "decreased"
        changes.append(f"Spend noise {direction} → {new_params['noise_factor']:.3f}")

    dip_delta = new_params.get("dip_probability", 0) - old_params.get("dip_probability", 0.04)
    if abs(dip_delta) > 0.02:
        changes.append(f"Dip probability raised → {new_params.get('dip_probability', 0):.2f}")

    jitter_delta = new_params.get("login_jitter", 1) - old_params.get("login_jitter", 1)
    if jitter_delta > 0:
        changes.append(f"Login jitter increased → ±{new_params.get('login_jitter', 1)}")

    strike_delta = new_params.get("strike_week_offset", 0) - old_params.get("strike_week_offset", 0)
    if strike_delta != 0:
        changes.append(f"Bust-out week shifted by {strike_delta:+d} weeks")

    surge_delta = new_params.get("surge_multiplier_cap", 20.0) - old_params.get("surge_multiplier_cap", 20.0)
    if surge_delta < -0.5:
        changes.append(f"Bust-out magnitude reduced → {new_params.get('surge_multiplier_cap', 20.0):.1f}x surge cap")

    if not changes:
        changes.append("Minor parameter drift (undetected — no major mutation needed)")

    return "; ".join(changes)
