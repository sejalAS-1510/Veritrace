import numpy as np
from typing import Dict, Any, List, Optional, Tuple

def extract_features(timeline: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extracts behavioral fingerprint features from an identity's weekly timeline.
    Focuses on incubation patterns (robotic linearity, unnatural regularity, zero variance).
    """
    if not timeline or len(timeline) < 3:
        return {
            "spend_smoothness": 0.0,
            "spend_monotonicity": 0.0,
            "login_regularity": 0.0,
            "variance_score": 0.5
        }

    # Find if there is a fraud strike and isolate the incubation window
    strike_idx = None
    for i, t in enumerate(timeline):
        if t.get("fraud_strike", False):
            strike_idx = i
            break
            
    # For trajectory evaluation, evaluate pre-strike incubation behavior (e.g. weeks 1-22)
    # If no explicit strike flag, examine either full timeline or up to last 2 weeks if large jump
    if strike_idx is not None and strike_idx >= 3:
        incubation_data = timeline[:strike_idx]
    else:
        incubation_data = timeline

    spends = np.array([float(t.get("spend", 0.0)) for t in incubation_data], dtype=np.float64)
    logins = np.array([float(t.get("login_count", 0.0)) for t in incubation_data], dtype=np.float64)
    n = len(spends)

    # 1. Spend Monotonicity: Proportion of weeks with monotonic non-decreasing spend
    # Sleeper agents incubated by scripts almost strictly ramp up spend week over week
    diffs = np.diff(spends)
    positive_diffs = np.sum(diffs >= -0.01)
    spend_monotonicity = float(positive_diffs / max(1, len(diffs)))

    # 2. Spend Smoothness: Goodness of fit (R^2) or standard deviation of second differences
    # Scripted sleeper accounts follow an uncanny straight line: y = a + b * week
    weeks_arr = np.arange(1, n + 1, dtype=np.float64)
    if n >= 3 and np.std(spends) > 1e-4:
        # Linear fit
        coeffs = np.polyfit(weeks_arr, spends, 1)
        fitted = np.polyval(coeffs, weeks_arr)
        residuals = spends - fitted
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((spends - np.mean(spends)) ** 2)
        r2 = 1.0 - (ss_res / (ss_tot + 1e-8))
        # Ensure clamped between 0.0 and 1.0
        spend_smoothness = float(np.clip(r2, 0.0, 1.0))
        # Penalty if slope is negative (sleeper ramps UP, not down)
        if coeffs[0] <= 0:
            spend_smoothness *= 0.3
    else:
        spend_smoothness = 0.5

    # 3. Login Regularity: Scripted accounts exhibit near-zero variance in login counts
    # e.g., exactly 5 logins every single week (+- 0.2 std dev)
    login_std = float(np.std(logins))
    # Normalized regularity: std of 0 -> 1.0, std >= 3.0 -> near 0.0
    login_regularity = float(1.0 / (1.0 + login_std))

    # 4. Variance Score (Coefficient of Variation of spend deltas)
    # Lower natural variance is a strong indicator of automated synthetic generation
    mean_spend = float(np.mean(spends))
    if mean_spend > 0:
        cv = float(np.std(spends) / mean_spend)
        # Bounded between 0 and 1
        variance_score = float(np.clip(cv, 0.0, 1.0))
    else:
        variance_score = 0.5

    return {
        "spend_smoothness": round(spend_smoothness, 4),
        "spend_monotonicity": round(spend_monotonicity, 4),
        "login_regularity": round(login_regularity, 4),
        "variance_score": round(variance_score, 4)
    }

def score_trajectory(timeline: List[Dict[str, Any]], threshold: float = 0.65) -> Dict[str, Any]:
    """
    Evaluates trajectory features to compute a composite risk score (0.0 - 1.0),
    a binary flagged verdict, and the earliest detection week (flag_week).
    """
    if not timeline or len(timeline) < 2:
        return {
            "risk_score": 0.1,
            "flagged": False,
            "flag_week": None,
            "features": {
                "spend_smoothness": 0.0,
                "spend_monotonicity": 0.0,
                "login_regularity": 0.0,
                "variance_score": 0.5
            }
        }

    features = extract_features(timeline)
    
    # Synthetic sleeper indicators:
    # High monotonicity (0.35), High smoothness/linearity (0.35), High login regularity (0.20), Low organic noise (0.10)
    monotonicity_weight = 0.35
    smoothness_weight = 0.35
    regularity_weight = 0.20
    low_variance_weight = 0.10

    raw_score = (
        monotonicity_weight * features["spend_monotonicity"] +
        smoothness_weight * features["spend_smoothness"] +
        regularity_weight * features["login_regularity"] +
        low_variance_weight * (1.0 - min(1.0, features["variance_score"] * 1.5))
    )

    # Check if there is an explicit terminal fraud strike in the timeline
    has_strike = any(t.get("fraud_strike", False) for t in timeline)
    if has_strike:
        raw_score = max(raw_score, 0.95)

    risk_score = round(float(np.clip(raw_score, 0.02, 0.99)), 3)
    flagged = bool(risk_score >= threshold)

    # Find earliest detection week (flag_week) by simulating rolling evaluation
    flag_week = None
    if flagged:
        for w in range(4, len(timeline) + 1):
            sub_timeline = timeline[:w]
            sub_feats = extract_features(sub_timeline)
            sub_score = (
                monotonicity_weight * sub_feats["spend_monotonicity"] +
                smoothness_weight * sub_feats["spend_smoothness"] +
                regularity_weight * sub_feats["login_regularity"] +
                low_variance_weight * (1.0 - min(1.0, sub_feats["variance_score"] * 1.5))
            )
            if sub_score >= threshold:
                flag_week = w
                break
        
        if flag_week is None:
            # Fallback if flagged primarily at terminal strike
            flag_week = min(len(timeline), 12)

    return {
        "risk_score": risk_score,
        "flagged": flagged,
        "flag_week": flag_week,
        "features": features
    }
