"""
VeriTrace Sentinel — Unified Scoring Engine
Combines three detection layers:

    Layer 1 — XGBoost (trained on benchmark dataset)
    Layer 2 — Isolation Forest (anomaly detection)
    Layer 3 — Trajectory analysis (R², monotonicity, login regularity)

score_trajectory(timeline, threshold)
    → Used by the adversarial loop and startup seed.
    → Falls back to trajectory-only when models are not loaded.

score_full(timeline, threshold)
    → Used by api/main.py for richer scoring that includes ML models.
    → Returns same shape as score_trajectory + extra ml_* fields.

The ML models are loaded once at module import and reused.
If they are missing (dev environment without models), the system
gracefully falls back to trajectory-only scoring.
"""

import os
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ─── Model paths ─────────────────────────────────────────────────────────────

_SENTINEL_DIR = os.path.dirname(os.path.abspath(__file__))
_MODEL_DIR = os.path.join(_SENTINEL_DIR, "models")
_XGB_MODEL_PATH = os.path.join(_MODEL_DIR, "xgboost_unified_fraud_model.pkl")
_IF_MODEL_PATH = os.path.join(_MODEL_DIR, "isolation_forest_anomaly_model.joblib")
_IF_SCALER_PATH = os.path.join(_MODEL_DIR, "isolation_forest_scaler.joblib")
_IF_THRESHOLD_PATH = os.path.join(_MODEL_DIR, "isolation_forest_threshold.joblib")

# XGBoost feature order — MUST match training
ML_FEATURES = [
    "transaction_amount",
    "account_age",
    "transaction_count",
    "avg_transaction_amount",
    "std_transaction_amount",
    "max_transaction_amount",
    "avg_time_gap",
    "std_time_gap",
    "cash_out_ratio",
    "payment_ratio",
    "transfer_ratio",
    "debit_ratio",
]

# ─── Lazy model loading ───────────────────────────────────────────────────────

_xgb_model = None
_if_model = None
_if_scaler = None
_if_threshold = None
_models_loaded = False
_models_available = False


def _load_models() -> None:
    global _xgb_model, _if_model, _if_scaler, _if_threshold, _models_loaded, _models_available
    if _models_loaded:
        return
    _models_loaded = True

    try:
        import joblib

        if not os.path.exists(_XGB_MODEL_PATH):
            logger.warning("XGBoost model not found at %s — using trajectory-only scoring", _XGB_MODEL_PATH)
            return

        _xgb_model = joblib.load(_XGB_MODEL_PATH)

        if (
            os.path.exists(_IF_MODEL_PATH)
            and os.path.exists(_IF_SCALER_PATH)
            and os.path.exists(_IF_THRESHOLD_PATH)
        ):
            _if_model = joblib.load(_IF_MODEL_PATH)
            _if_scaler = joblib.load(_IF_SCALER_PATH)
            _if_threshold = joblib.load(_IF_THRESHOLD_PATH)
            logger.info("Sentinel: XGBoost + Isolation Forest loaded successfully")
        else:
            logger.warning("Isolation Forest model files missing — using XGBoost only")

        _models_available = True

    except Exception as exc:
        logger.error("Failed to load Sentinel ML models: %s — falling back to trajectory scoring", exc)


# Load at import time (non-blocking — catches all errors)
try:
    _load_models()
except Exception:
    pass


# ─── Layer 1 helpers: convert weekly timeline to ML features ─────────────────

def _timeline_to_ml_features(timeline: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """
    Converts a weekly timeline dict (from Forge) into the 12 ML features
    that the XGBoost model was trained on.

    The XGBoost model was trained on transaction-level data. We aggregate
    the weekly timeline into account-level statistics that approximate
    the same 12 features.
    """
    if not timeline or len(timeline) < 2:
        return None

    spends = [float(t.get("spend", 0.0)) for t in timeline]
    n = len(spends)

    # transaction_amount: last transaction amount (most recent week)
    transaction_amount = spends[-1]

    # account_age: total weeks covered
    account_age = float(n)

    # transaction_count: total weeks with activity
    transaction_count = float(sum(1 for s in spends if s > 0))

    # historical amount stats (exclude current week)
    history = spends[:-1] if len(spends) > 1 else spends
    avg_ta = float(np.mean(history)) if history else 0.0
    std_ta = float(np.std(history)) if history else 0.0
    max_ta = float(np.max(history)) if history else 0.0

    # time gaps (week-over-week)
    weeks = [float(t.get("week", i + 1)) for i, t in enumerate(timeline)]
    gaps = [weeks[i + 1] - weeks[i] for i in range(len(weeks) - 1)]
    avg_gap = float(np.mean(gaps)) if gaps else 1.0
    std_gap = float(np.std(gaps)) if gaps else 0.0

    # transaction type ratios — derived from fraud_strike and context
    # (Forge timelines don't have explicit payment_channel, so we proxy:
    #  fraud_strike week = CASH_OUT, everything else = PAYMENT)
    n_cashout = sum(1 for t in timeline if t.get("fraud_strike", False))
    n_payment = max(0, n - n_cashout)
    cash_out_ratio = n_cashout / max(1, n)
    payment_ratio = n_payment / max(1, n)
    transfer_ratio = 0.0
    debit_ratio = 0.0

    return {
        "transaction_amount": transaction_amount,
        "account_age": account_age,
        "transaction_count": transaction_count,
        "avg_transaction_amount": avg_ta,
        "std_transaction_amount": std_ta,
        "max_transaction_amount": max_ta,
        "avg_time_gap": avg_gap,
        "std_time_gap": std_gap,
        "cash_out_ratio": cash_out_ratio,
        "payment_ratio": payment_ratio,
        "transfer_ratio": transfer_ratio,
        "debit_ratio": debit_ratio,
    }


def _xgboost_score(timeline: List[Dict[str, Any]]) -> Optional[float]:
    """
    Returns XGBoost fraud probability [0, 1] for the timeline.
    Returns None if models are not available.
    """
    if not _models_available or _xgb_model is None:
        return None

    ml_feats = _timeline_to_ml_features(timeline)
    if ml_feats is None:
        return None

    try:
        import pandas as pd
        row = pd.DataFrame([{k: ml_feats[k] for k in ML_FEATURES}])
        prob = float(_xgb_model.predict_proba(row)[0, 1])
        return float(np.clip(prob, 0.0, 1.0))
    except Exception as exc:
        logger.debug("XGBoost prediction failed: %s", exc)
        return None


def _isolation_forest_score(timeline: List[Dict[str, Any]]) -> Optional[float]:
    """
    Returns Isolation Forest anomaly score [0, 1] for the timeline.
    Returns None if models are not available.
    """
    if not _models_available or _if_model is None or _if_scaler is None:
        return None

    ml_feats = _timeline_to_ml_features(timeline)
    if ml_feats is None:
        return None

    try:
        import pandas as pd
        row = pd.DataFrame([{k: ml_feats[k] for k in ML_FEATURES}])
        scaled = _if_scaler.transform(row)
        raw_score = -float(_if_model.decision_function(scaled)[0])

        # Normalise relative to threshold
        threshold = float(_if_threshold) if _if_threshold is not None else 0.0
        scale = max(abs(threshold) * 0.5, 0.1)
        normalised = 1.0 / (1.0 + np.exp(-(raw_score - threshold) / scale))
        return float(np.clip(normalised, 0.0, 1.0))
    except Exception as exc:
        logger.debug("Isolation Forest prediction failed: %s", exc)
        return None


# ─── Layer 3: Trajectory feature extraction ──────────────────────────────────

def extract_features(timeline: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Six incubation-period behavioural features.
    Works on pre-strike data only so the bust-out doesn't contaminate R².
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

    # Find fraud strike
    strike_idx: Optional[int] = None
    for i, t in enumerate(timeline):
        if t.get("fraud_strike", False):
            strike_idx = i
            break

    if strike_idx is not None and strike_idx >= 3:
        incubation = timeline[:strike_idx]
        final_spend = float(timeline[strike_idx].get("spend", 0.0))
    else:
        incubation = timeline
        final_spend = 0.0

    spends = np.array([float(t.get("spend", 0.0)) for t in incubation], dtype=np.float64)
    logins = np.array([float(t.get("login_count", 0.0)) for t in incubation], dtype=np.float64)
    n = len(spends)

    # Spend monotonicity
    diffs = np.diff(spends)
    spend_monotonicity = float(np.sum(diffs >= -0.01) / max(1, len(diffs)))

    # Spend smoothness (R²)
    weeks_arr = np.arange(1, n + 1, dtype=np.float64)
    if n >= 3 and np.std(spends) > 1e-4:
        coeffs = np.polyfit(weeks_arr, spends, 1)
        fitted = np.polyval(coeffs, weeks_arr)
        ss_res = float(np.sum((spends - fitted) ** 2))
        ss_tot = float(np.sum((spends - np.mean(spends)) ** 2))
        r2 = 1.0 - (ss_res / (ss_tot + 1e-8))
        spend_smoothness = float(np.clip(r2, 0.0, 1.0))
        if coeffs[0] <= 0:
            spend_smoothness *= 0.3
    else:
        spend_smoothness = 0.5

    # Login regularity
    login_std = float(np.std(logins))
    login_regularity = float(1.0 / (1.0 + login_std))

    # Variance (CV)
    mean_spend = float(np.mean(spends))
    variance_score = float(np.clip(np.std(spends) / mean_spend, 0.0, 1.0)) if mean_spend > 1e-4 else 0.5

    # Bust-out ratio
    if mean_spend > 1e-4 and final_spend > 0:
        bust_out_ratio = float(np.clip((final_spend / mean_spend - 1.0) / 19.0, 0.0, 1.0))
    else:
        bust_out_ratio = 0.0

    # Device change rate
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


def transaction_anomaly_score(timeline: List[Dict[str, Any]]) -> float:
    """Z-score of the final transaction vs account's own history."""
    if not timeline or len(timeline) < 4:
        return 0.0
    spends = [float(t.get("spend", 0.0)) for t in timeline]
    final = spends[-1]
    history = np.array(spends[:-1], dtype=np.float64)
    if len(history) < 3:
        return 0.0
    mu = float(np.mean(history))
    sigma = float(np.std(history))
    max_hist = float(np.max(history))
    effective_sigma = max(sigma, mu * 0.20, (max_hist - mu) * 0.5 + 1e-8)
    z = abs(final - mu) / effective_sigma
    score = float(1.0 - np.exp(-z / 6.0))
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def _trajectory_risk_score(features: Dict[str, float], tx_anomaly: float) -> float:
    """Compute the trajectory-only composite risk (0-1)."""
    dcr = features["device_change_rate"]
    device_signal = float(1.0 - min(1.0, abs(dcr - 0.06) / 0.06)) if dcr < 0.12 else 0.5

    traj = (
        0.30 * features["spend_smoothness"]
        + 0.25 * features["spend_monotonicity"]
        + 0.15 * features["login_regularity"]
        + 0.10 * features["bust_out_ratio"]
        + 0.10 * (1.0 - min(1.0, features["variance_score"] * 1.5))
        + 0.10 * device_signal
    )
    return float(np.clip(0.60 * traj + 0.40 * tx_anomaly, 0.02, 0.99))


# ─── Public: trajectory-only scorer (used by adversarial loop) ───────────────

def score_trajectory(
    timeline: List[Dict[str, Any]],
    threshold: float = 0.55,
) -> Dict[str, Any]:
    """
    Trajectory + transaction anomaly scoring.
    Used by the adversarial loop (fast, no ML model overhead per round).

    Returns:
        risk_score, flagged, flag_week, features, risk_breakdown
    """
    if not timeline or len(timeline) < 2:
        empty = {
            "spend_smoothness": 0.0, "spend_monotonicity": 0.0,
            "login_regularity": 0.0, "variance_score": 0.5,
            "bust_out_ratio": 0.0, "device_change_rate": 0.0,
        }
        return {
            "risk_score": 0.05, "flagged": False, "flag_week": None,
            "features": empty,
            "risk_breakdown": {"trajectory_risk": 0.05, "transaction_anomaly": 0.0},
        }

    features = extract_features(timeline)
    tx_anomaly = transaction_anomaly_score(timeline)

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

    raw_score = 0.60 * trajectory_risk + 0.40 * tx_anomaly
    risk_score = round(float(np.clip(raw_score, 0.02, 0.99)), 3)
    flagged = bool(risk_score >= threshold)

    # Rolling flag_week detection
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
            if 0.60 * sub_traj + 0.40 * sub_tx >= threshold:
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


# ─── Public: full ML-backed scorer (used by api/main.py endpoints) ───────────

def score_full(
    timeline: List[Dict[str, Any]],
    threshold: float = 0.55,
) -> Dict[str, Any]:
    """
    Three-layer fusion score:
        40% — XGBoost ML model (trained on benchmark dataset)
        20% — Isolation Forest anomaly score
        40% — Trajectory + transaction anomaly (rule-based)

    Falls back to trajectory-only (threshold=0.55) when ML models
    are not available (e.g., local dev without model files).

    Returns the same shape as score_trajectory plus extra fields:
        ml_xgb_score, ml_if_score, ml_available, risk_category, action
    """
    # Always compute trajectory layer using the same threshold
    traj_result = score_trajectory(timeline, threshold=threshold)
    features = traj_result["features"]
    tx_anomaly = traj_result["risk_breakdown"]["transaction_anomaly"]
    trajectory_risk = traj_result["risk_breakdown"]["trajectory_risk"]

    xgb_score = _xgboost_score(timeline)
    if_score = _isolation_forest_score(timeline)

    if _models_available and xgb_score is not None:
        # XGBoost was trained on real payment transactions.
        # Our weekly timeline proxy features give lower XGBoost scores (~0.1-0.3).
        # When XGBoost fires strongly (>0.4), use full fusion.
        # When it's low (proxy data mismatch), blend conservatively so the
        # well-calibrated trajectory signal stays dominant.
        if xgb_score >= 0.40:
            # Strong XGBoost signal — full fusion
            if if_score is not None:
                raw = 0.35 * xgb_score + 0.15 * if_score + 0.50 * traj_result["risk_score"]
            else:
                raw = 0.40 * xgb_score + 0.60 * traj_result["risk_score"]
        else:
            # Weak XGBoost signal (proxy data) — trajectory dominates
            xgb_boost = xgb_score * 0.10   # still incorporate as minor signal
            if_boost = (if_score or 0.0) * 0.05
            raw = traj_result["risk_score"] * 0.85 + xgb_boost + if_boost
        raw_score = round(float(np.clip(raw, 0.02, 0.99)), 3)
    else:
        # Fallback: trajectory only
        raw_score = traj_result["risk_score"]

    flagged = bool(raw_score >= threshold)

    # Risk category (0-100 scale)
    pct = raw_score * 100
    if pct < 30:
        risk_category = "LOW"
        action = "ALLOW"
    elif pct < 55:
        risk_category = "MEDIUM"
        action = "MONITOR"
    elif pct < 75:
        risk_category = "HIGH"
        action = "STEP_UP_VERIFICATION"
    else:
        risk_category = "CRITICAL"
        action = "BLOCK"

    return {
        "risk_score": raw_score,
        "risk_score_pct": round(raw_score * 100, 1),
        "flagged": flagged,
        "flag_week": traj_result["flag_week"],
        "features": features,
        "risk_breakdown": {
            "trajectory_risk": round(trajectory_risk, 3),
            "transaction_anomaly": round(tx_anomaly, 3),
            "xgb_score": round(xgb_score, 3) if xgb_score is not None else None,
            "if_score": round(if_score, 3) if if_score is not None else None,
        },
        "risk_category": risk_category,
        "action": action,
        "ml_available": _models_available,
    }


def models_loaded() -> bool:
    """Returns True if ML models are available for inference."""
    return _models_available
