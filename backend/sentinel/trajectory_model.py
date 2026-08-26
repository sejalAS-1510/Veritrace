"""
VeriTrace Sentinel — Trajectory & Transaction Anomaly Model
Member 2 owns this file (feature engineering + detection).
Member 3 calls score_trajectory() from the adversarial loop.

Detection has THREE independent layers so Forge must beat all three to evade:
  1. Trajectory features  — incubation-period behavioural fingerprint
  2. Transaction anomaly  — how far the final event deviates from account history
  3. (Graph similarity    — handled separately in similarity_graph.py)

The `has_strike` blunt override has been removed so that Forge's mutation
engine can actually produce evasion — making the arms-race demo real.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple


# ─── Layer 1: Incubation trajectory features ─────────────────────────────────

def extract_features(timeline: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extracts four incubation-period behavioural features.

    Isolates the pre-strike window so the bust-out week doesn't contaminate
    the trajectory signal — but also returns a separate `bust_out_ratio`
    that measures the terminal anomaly.

    Returns
    -------
    dict with keys:
        spend_smoothness    — R² of linear fit on incubation spend (high = scripted)
        spend_monotonicity  — fraction of non-decreasing weeks      (high = scripted)
        login_regularity    — inverse of login std-dev              (high = scripted)
        variance_score      — coefficient of variation              (low  = scripted)
        bust_out_ratio      — final spend / mean incubation spend   (high = bust-out)
        device_change_rate  — device changes per week               (abnormal if 0 or spike)
    """
    if not timeline or len(timeline) < 3:
        return {
            "spend_smoothness": 0.0,
            "spend_monotonicity": 0.0,
            "login_regularity": 0.0,
            "variance_score": 0.5,
            "bust_out_ratio": 0.0,
            "device_change_rate": 0.0,
        }

    # Locate fraud strike week (first week flagged as fraud_strike=True)
    strike_idx: Optional[int] = None
    for i, t in enumerate(timeline):
        if t.get("fraud_strike", False):
            strike_idx = i
            break

    # Incubation = everything before the strike (or full timeline if no strike)
    if strike_idx is not None and strike_idx >= 3:
        incubation = timeline[:strike_idx]
        final_spend = float(timeline[strike_idx].get("spend", 0.0))
    else:
        incubation = timeline
        final_spend = 0.0

    spends = np.array([float(t.get("spend", 0.0)) for t in incubation], dtype=np.float64)
    logins = np.array([float(t.get("login_count", 0.0)) for t in incubation], dtype=np.float64)
    n = len(spends)

    # ── 1. Spend Monotonicity ─────────────────────────────────────────────────
    diffs = np.diff(spends)
    spend_monotonicity = float(np.sum(diffs >= -0.01) / max(1, len(diffs)))

    # ── 2. Spend Smoothness (R²) ──────────────────────────────────────────────
    weeks_arr = np.arange(1, n + 1, dtype=np.float64)
    if n >= 3 and np.std(spends) > 1e-4:
        coeffs = np.polyfit(weeks_arr, spends, 1)
        fitted = np.polyval(coeffs, weeks_arr)
        ss_res = float(np.sum((spends - fitted) ** 2))
        ss_tot = float(np.sum((spends - np.mean(spends)) ** 2))
        r2 = 1.0 - (ss_res / (ss_tot + 1e-8))
        spend_smoothness = float(np.clip(r2, 0.0, 1.0))
        # Negative slope → not a ramp-up attacker → reduce suspicion
        if coeffs[0] <= 0:
            spend_smoothness *= 0.3
    else:
        spend_smoothness = 0.5

    # ── 3. Login Regularity ───────────────────────────────────────────────────
    login_std = float(np.std(logins))
    login_regularity = float(1.0 / (1.0 + login_std))

    # ── 4. Variance (CV of spend) ─────────────────────────────────────────────
    mean_spend = float(np.mean(spends))
    if mean_spend > 1e-4:
        variance_score = float(np.clip(np.std(spends) / mean_spend, 0.0, 1.0))
    else:
        variance_score = 0.5

    # ── 5. Bust-out ratio ─────────────────────────────────────────────────────
    # How many times bigger is the final spend vs the incubation average?
    # Real humans can have large purchases; ratio > 8x is suspicious.
    if mean_spend > 1e-4 and final_spend > 0:
        raw_ratio = final_spend / mean_spend
        # Normalise: ratio=1 → 0.0, ratio=15 → ~0.93, ratio≥20 → capped at 1.0
        bust_out_ratio = float(np.clip((raw_ratio - 1.0) / 19.0, 0.0, 1.0))
    else:
        bust_out_ratio = 0.0

    # ── 6. Device change rate ─────────────────────────────────────────────────
    device_changes = sum(1 for t in incubation if t.get("new_device", False))
    device_change_rate = float(device_changes / max(1, len(incubation)))

    return {
        "spend_smoothness": round(spend_smoothness, 4),
        "spend_monotonicity": round(spend_monotonicity, 4),
        "login_regularity": round(login_regularity, 4),
        "variance_score": round(variance_score, 4),
        "bust_out_ratio": round(bust_out_ratio, 4),
        "device_change_rate": round(device_change_rate, 4),
    }


# ─── Layer 2: Transaction anomaly signal ─────────────────────────────────────

def transaction_anomaly_score(timeline: List[Dict[str, Any]]) -> float:
    """
    Measures how anomalous the FINAL transaction is relative to the
    account's own spending history.

    Uses a modified z-score that accounts for the natural range of spending
    rather than the std-dev alone — this way Forge can reduce the anomaly
    signal by expanding incubation variance in later rounds.

    Returns a score in [0, 1]:
        0.0 = perfectly normal for this account
        1.0 = extreme outlier
    """
    if not timeline or len(timeline) < 4:
        return 0.0

    spends = [float(t.get("spend", 0.0)) for t in timeline]
    final = spends[-1]
    history = np.array(spends[:-1], dtype=np.float64)

    if len(history) < 3:
        return 0.0

    mu = float(np.mean(history))
    sigma = float(np.std(history))
    # Use max observed spend as upper reference — if the account's own
    # history already had a large spike, the final event is less anomalous
    max_hist = float(np.max(history))

    # Effective sigma: at least 20% of mean (prevents near-zero std making
    # every deviation look like z=100), and at least half the max-mean gap
    effective_sigma = max(sigma, mu * 0.20, (max_hist - mu) * 0.5 + 1e-8)

    z = abs(final - mu) / effective_sigma

    # Map z-score → [0, 1]:  z≤1 → 0.22, z=3 → 0.53, z=6 → 0.78, z=12+ → ~1.0
    score = float(1.0 - np.exp(-z / 6.0))
    return round(float(np.clip(score, 0.0, 1.0)), 4)


# ─── Combined scorer ──────────────────────────────────────────────────────────

def score_trajectory(
    timeline: List[Dict[str, Any]],
    threshold: float = 0.55,
) -> Dict[str, Any]:
    """
    Evaluates a timeline using all three Sentinel signals and returns:
        risk_score   — composite 0–1 score
        flagged      — True if risk_score >= threshold
        flag_week    — earliest week Sentinel would have triggered
        features     — full feature dict
        risk_breakdown — per-layer contribution (useful for explainability)

    Weights
    -------
    The three components and their contribution to the final risk score:

        trajectory_risk   (60%)
            = 0.30 * smoothness + 0.25 * monotonicity
            + 0.15 * regularity + 0.10 * bust_out_ratio
            + 0.10 * (1 - variance) + 0.10 * device_change_signal

        transaction_anomaly (25%)  — final event z-score

        These combine as:
            raw = 0.60 * trajectory + 0.40 * anomaly

    Why these weights?
    - Trajectory is the primary long-term incubation signal.
    - Transaction anomaly is strong evidence but a good attacker can
      reduce bust-out size, so it must not dominate alone.
    - This means Forge must break BOTH the trajectory AND the anomaly
      signals simultaneously to fully evade Sentinel — much harder.
    """
    if not timeline or len(timeline) < 2:
        empty_features = {
            "spend_smoothness": 0.0,
            "spend_monotonicity": 0.0,
            "login_regularity": 0.0,
            "variance_score": 0.5,
            "bust_out_ratio": 0.0,
            "device_change_rate": 0.0,
        }
        return {
            "risk_score": 0.05,
            "flagged": False,
            "flag_week": None,
            "features": empty_features,
            "risk_breakdown": {"trajectory_risk": 0.05, "transaction_anomaly": 0.0},
        }

    features = extract_features(timeline)
    tx_anomaly = transaction_anomaly_score(timeline)

    # ── Trajectory sub-score ──────────────────────────────────────────────────
    # Device change signal: either 0 (no changes = too clean) or spike (takeover)
    # Very low rate is suspicious for sleepers; very high rate is also suspicious
    dcr = features["device_change_rate"]
    device_signal = float(1.0 - min(1.0, abs(dcr - 0.06) / 0.06)) if dcr < 0.12 else 0.5

    trajectory_risk = (
        0.30 * features["spend_smoothness"]
        + 0.25 * features["spend_monotonicity"]
        + 0.15 * features["login_regularity"]
        + 0.10 * features["bust_out_ratio"]
        + 0.10 * (1.0 - min(1.0, features["variance_score"] * 1.5))
        + 0.10 * device_signal
    )

    # ── Combined risk ─────────────────────────────────────────────────────────
    raw_score = 0.60 * trajectory_risk + 0.40 * tx_anomaly
    risk_score = round(float(np.clip(raw_score, 0.02, 0.99)), 3)
    flagged = bool(risk_score >= threshold)

    # ── Earliest detection week (rolling simulation) ─────────────────────────
    flag_week: Optional[int] = None
    if flagged:
        for w in range(4, len(timeline) + 1):
            sub = timeline[:w]
            sub_feats = extract_features(sub)
            sub_tx = transaction_anomaly_score(sub)

            sub_dcr = sub_feats["device_change_rate"]
            sub_device = float(1.0 - min(1.0, abs(sub_dcr - 0.06) / 0.06)) if sub_dcr < 0.12 else 0.5

            sub_traj = (
                0.30 * sub_feats["spend_smoothness"]
                + 0.25 * sub_feats["spend_monotonicity"]
                + 0.15 * sub_feats["login_regularity"]
                + 0.10 * sub_feats["bust_out_ratio"]
                + 0.10 * (1.0 - min(1.0, sub_feats["variance_score"] * 1.5))
                + 0.10 * sub_device
            )
            sub_score = 0.60 * sub_traj + 0.40 * sub_tx
            if sub_score >= threshold:
                flag_week = w
                break

    return {
        "risk_score": risk_score,
        "flagged": flagged,
        "flag_week": flag_week,
        "features": features,
        "risk_breakdown": {
            "trajectory_risk": round(trajectory_risk, 3),
            "transaction_anomaly": round(tx_anomaly, 3),
        },
    }
