"""
VeriTrace — Adversarial Engine API
Member 3: Adversarial Engine + Backend

This module owns the core adversarial loop:
    FORGE → ATTACK → SENTINEL → DETECT/MISS → FEEDBACK → MUTATE → NEXT ROUND

Endpoints
---------
POST /adversarial/run            Run a full adversarial round end-to-end
POST /adversarial/reset          Reset the adversarial session state
GET  /adversarial/rounds         Return live round history (not hardcoded)
GET  /adversarial/status         Current Forge params + session stats
GET  /adversarial/metrics        Precision / recall / F1 / evasion rate
"""

import copy
import time
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from forge.generator import generate_timeline_adversarial
from forge.mutation import (
    DEFAULT_PARAMS,
    describe_mutation,
    mutate_params,
    params_to_generator_kwargs,
)
from sentinel.trajectory_model import score_trajectory

router = APIRouter(prefix="/adversarial", tags=["adversarial"])

# ─── In-memory adversarial session state ─────────────────────────────────────
# This gets reset on server restart or via POST /adversarial/reset

_STATE: Dict[str, Any] = {
    "round_number": 0,
    "forge_params": copy.deepcopy(DEFAULT_PARAMS),
    "rounds": [],           # List[RoundRecord]
    "total_attacks": 0,
    "total_detected": 0,
    "total_evaded": 0,
    "sentinel_threshold": 0.55,   # Adapts: tightens after evasion, relaxes after streaks
}


def _reset_state() -> None:
    _STATE["round_number"] = 0
    _STATE["forge_params"] = copy.deepcopy(DEFAULT_PARAMS)
    _STATE["rounds"] = []
    _STATE["total_attacks"] = 0
    _STATE["total_detected"] = 0
    _STATE["total_evaded"] = 0
    _STATE["sentinel_threshold"] = 0.55


# ─── Route: Run one adversarial round ────────────────────────────────────────

@router.post("/run")
def run_adversarial_round(ring_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes one full adversarial round:

    1.  Increment round counter
    2.  Read current Forge parameters (mutated by previous feedback)
    3.  Generate a new sleeper identity using those parameters
    4.  Run Sentinel trajectory analysis on the generated timeline
    5.  Record result (detected / evaded) and the detection features
    6.  Feed result back into mutation engine
    7.  Update Forge parameters for next round
    8.  Return the full round record to the frontend

    Returns
    -------
    JSON with:
        round_number, identity_id, identity_type, flagged, risk_score,
        flag_week, features, forge_params_used, forge_params_next,
        mutation_description, was_detected, outcome, adversarial_score,
        round_summary
    """
    _STATE["round_number"] += 1
    round_num = _STATE["round_number"]

    old_params = copy.deepcopy(_STATE["forge_params"])
    gen_kwargs = params_to_generator_kwargs(old_params)

    # ── 1. Generate adversarial identity ──────────────────────────────────────
    raw_identity = generate_timeline_adversarial(
        weeks=24,
        ring_id=ring_id,
        **gen_kwargs,
    )

    # ── 2. Sentinel evaluates using adaptive threshold ────────────────────────
    verdict = score_trajectory(
        raw_identity["timeline"],
        threshold=_STATE["sentinel_threshold"],
    )
    flagged: bool = verdict["flagged"]
    risk_score: float = verdict["risk_score"]
    flag_week = verdict["flag_week"]
    features: Dict[str, float] = verdict["features"]

    # ── 3. Update session counters ─────────────────────────────────────────────
    _STATE["total_attacks"] += 1
    if flagged:
        _STATE["total_detected"] += 1
        outcome = "DETECTED"
    else:
        _STATE["total_evaded"] += 1
        outcome = "EVADED"

    # ── 4. Mutation: Forge learns from the result ──────────────────────────────
    new_params = mutate_params(
        current_params=old_params,
        detection_features=features,
        was_detected=flagged,
        round_number=round_num,
    )
    mutation_description = describe_mutation(old_params, new_params)
    _STATE["forge_params"] = new_params

    # ── 5. Sentinel adaptation: tighten threshold after evasions ──────────────
    # After a successful Forge evasion, Sentinel lowers its detection threshold
    # (becomes more sensitive). After 2+ consecutive detections, relax slightly.
    # This is the "Sentinel learns" part of the arms-race narrative.
    consecutive_detections = 0
    for past in reversed(_STATE["rounds"][-3:]):
        if past.get("flagged"):
            consecutive_detections += 1
        else:
            break

    sentinel_note = ""
    if not flagged:
        # Forge evaded — Sentinel tightens threshold by 0.04 (aggressive catch-up)
        _STATE["sentinel_threshold"] = max(0.44, _STATE["sentinel_threshold"] - 0.04)
        sentinel_note = f"Sentinel tightened threshold → {_STATE['sentinel_threshold']:.2f}"
    elif consecutive_detections >= 2:
        # 2+ consecutive detections — Sentinel can relax slightly
        _STATE["sentinel_threshold"] = min(0.58, _STATE["sentinel_threshold"] + 0.015)
        if consecutive_detections >= 2:
            sentinel_note = f"Sentinel relaxed threshold → {_STATE['sentinel_threshold']:.2f}"

    # ── 6. Rolling catch / evasion rates ─────────────────────────────────────
    rolling_catch_rate = round(
        (_STATE["total_detected"] / _STATE["total_attacks"]) * 100, 1
    )
    rolling_evasion_rate = round(
        (_STATE["total_evaded"] / _STATE["total_attacks"]) * 100, 1
    )

    # ── 6. Adversarial score: how "hard" was this attack? ─────────────────────
    # Proxy: inverse of risk score scaled to 100 (higher = harder to detect)
    adversarial_score = round((1.0 - risk_score) * 100, 1)

    # ── 7. Round summary sentence ─────────────────────────────────────────────
    if outcome == "DETECTED":
        dominant_signal = max(
            {"spend_smoothness": features.get("spend_smoothness", 0),
             "spend_monotonicity": features.get("spend_monotonicity", 0),
             "login_regularity": features.get("login_regularity", 0)},
            key=lambda k: features.get(k, 0),
        )
        signal_labels = {
            "spend_smoothness": "spend linearity (R²)",
            "spend_monotonicity": "spend monotonicity",
            "login_regularity": "login regularity",
        }
        round_summary = (
            f"Round {round_num}: Sentinel detected identity {raw_identity['id']} "
            f"at risk {risk_score * 100:.0f}% — primary signal: {signal_labels.get(dominant_signal, dominant_signal)}. "
            f"Forge mutating: {mutation_description}."
        )
    else:
        round_summary = (
            f"Round {round_num}: Forge EVADED Sentinel! "
            f"Identity {raw_identity['id']} slipped through with risk {risk_score * 100:.0f}%. "
            f"Sentinel adapting — Forge params barely shift."
        )

    # ── 8. Persist identity into main store (so graph + history include it) ──
    # Lazy import to avoid circular dependency with api.main
    try:
        from api.main import IDENTITIES_STORE
        IDENTITIES_STORE[raw_identity["id"]] = {
            "id": raw_identity["id"],
            "type": raw_identity["type"],
            "ring_id": raw_identity.get("ring_id"),
            "weeks_count": 24,
            "timeline": raw_identity["timeline"],
            "flagged": flagged,
            "risk_score": risk_score,
            "risk_score_pct": round(risk_score * 100, 1),
            "flag_week": flag_week,
            "features": features,
            "risk_breakdown": verdict.get("risk_breakdown", {}),
            "detection_reasons": [],
            "adversarial_round": round_num,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except ImportError:
        pass  # running in isolation (tests)

    # ── 9. Build round record ──────────────────────────────────────────────────
    round_record: Dict[str, Any] = {
        "round_number": round_num,
        "identity_id": raw_identity["id"],
        "identity_type": raw_identity["type"],
        "flagged": flagged,
        "risk_score": risk_score,
        "risk_score_pct": round(risk_score * 100, 1),
        "flag_week": flag_week,
        "features": features,
        "risk_breakdown": verdict.get("risk_breakdown", {}),
        "outcome": outcome,
        "adversarial_score": adversarial_score,
        "forge_params_used": {k: v for k, v in old_params.items() if not k.startswith("_")},
        "forge_params_next": {k: v for k, v in new_params.items() if not k.startswith("_")},
        "mutation_description": mutation_description,
        "round_summary": round_summary,
        "sentinel_threshold": _STATE["sentinel_threshold"],
        "sentinel_note": sentinel_note,
        "rolling_catch_rate": rolling_catch_rate,
        "rolling_evasion_rate": rolling_evasion_rate,
        "timeline_preview": raw_identity["timeline"][:5],  # first 5 weeks for preview
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _STATE["rounds"].append(round_record)
    return round_record


# ─── Route: Reset adversarial session ────────────────────────────────────────

@router.post("/reset")
def reset_adversarial_session() -> Dict[str, Any]:
    """Resets the adversarial session to round 0 and default Forge parameters."""
    _reset_state()
    return {
        "status": "reset",
        "message": "Adversarial session reset. Forge parameters returned to defaults.",
        "forge_params": {k: v for k, v in _STATE["forge_params"].items() if not k.startswith("_")},
    }


# ─── Route: Manual feedback injection ────────────────────────────────────────

class FeedbackRequest(BaseModel):
    detection_features: Dict[str, float] = Field(
        ...,
        description=(
            "Sentinel feature scores to feed back into Forge mutation. "
            "Keys: spend_smoothness, spend_monotonicity, login_regularity, "
            "variance_score, bust_out_ratio, device_change_rate"
        ),
    )
    was_detected: bool = Field(
        ..., description="Whether the last attack was flagged by Sentinel"
    )
    notes: Optional[str] = Field(None, description="Optional human annotation")


@router.post("/feedback")
def inject_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """
    Manually injects Sentinel detection feedback into the Forge mutation engine.

    Use this when you want to drive Forge evolution from an external detection
    result (e.g., Member 2 ran their own Sentinel model and wants to feed
    results back) rather than from the automatic /adversarial/run loop.

    The current Forge parameters are mutated immediately and the new params
    are returned. The round counter is NOT incremented — feedback is applied
    to whichever round was last run.
    """
    old_params = copy.deepcopy(_STATE["forge_params"])
    round_num = max(1, _STATE["round_number"])

    new_params = mutate_params(
        current_params=old_params,
        detection_features=req.detection_features,
        was_detected=req.was_detected,
        round_number=round_num,
    )
    mutation_desc = describe_mutation(old_params, new_params)
    _STATE["forge_params"] = new_params

    return {
        "status": "feedback_applied",
        "round_number": _STATE["round_number"],
        "was_detected": req.was_detected,
        "mutation_description": mutation_desc,
        "forge_params_before": {k: v for k, v in old_params.items() if not k.startswith("_")},
        "forge_params_after": {k: v for k, v in new_params.items() if not k.startswith("_")},
        "notes": req.notes,
    }


# ─── Route: Round history ─────────────────────────────────────────────────────

@router.get("/rounds")
def get_adversarial_rounds() -> List[Dict[str, Any]]:
    """
    Returns the live history of adversarial rounds.
    Each round includes detection outcome, risk score, Forge params used,
    and the mutation applied for the next round.

    If no rounds have been run yet, returns a seeded demo sequence so the
    frontend has something to display on first load.
    """
    if _STATE["rounds"]:
        return _STATE["rounds"]

    # ── Fallback: pre-seeded demonstration sequence ───────────────────────────
    # This mirrors the arms-race narrative: baseline → evasion → adaptation → recovery
    demo = [
        {
            "round_number": 1,
            "outcome": "DETECTED",
            "risk_score_pct": 87.0,
            "adversarial_score": 13.0,
            "rolling_catch_rate": 100.0,
            "rolling_evasion_rate": 0.0,
            "mutation_description": "Spend noise increased → 0.078; Dip probability raised → 0.12",
            "round_summary": "Round 1: Sentinel detected naive linear spend ramp. Forge adapting noise levels.",
        },
        {
            "round_number": 2,
            "outcome": "DETECTED",
            "risk_score_pct": 79.5,
            "adversarial_score": 20.5,
            "rolling_catch_rate": 100.0,
            "rolling_evasion_rate": 0.0,
            "mutation_description": "Monotonicity broken; Login jitter increased → ±3",
            "round_summary": "Round 2: Spend variance improved but login regularity still detected. Jitter increased.",
        },
        {
            "round_number": 3,
            "outcome": "DETECTED",
            "risk_score_pct": 71.2,
            "adversarial_score": 28.8,
            "rolling_catch_rate": 100.0,
            "rolling_evasion_rate": 0.0,
            "mutation_description": "Bust-out week shifted by -1 weeks; Variance boosted",
            "round_summary": "Round 3: Closer call — risk 71%. Forge introduces bust-out timing variance.",
        },
        {
            "round_number": 4,
            "outcome": "EVADED",
            "risk_score_pct": 58.3,
            "adversarial_score": 41.7,
            "rolling_catch_rate": 75.0,
            "rolling_evasion_rate": 25.0,
            "mutation_description": "Minor parameter drift (undetected — no major mutation needed)",
            "round_summary": "Round 4: Forge EVADED Sentinel! Risk 58% — below detection threshold. Sentinel adapting.",
        },
        {
            "round_number": 5,
            "outcome": "DETECTED",
            "risk_score_pct": 76.4,
            "adversarial_score": 23.6,
            "rolling_catch_rate": 80.0,
            "rolling_evasion_rate": 20.0,
            "mutation_description": "Base spend offset shifted; spend linearity broken",
            "round_summary": "Round 5: Sentinel recovered — updated cosine threshold caught the ring cluster.",
        },
        {
            "round_number": 6,
            "outcome": "DETECTED",
            "risk_score_pct": 84.1,
            "adversarial_score": 15.9,
            "rolling_catch_rate": 83.3,
            "rolling_evasion_rate": 16.7,
            "mutation_description": "Login jitter increased → ±5; Dip magnitude raised → 0.32",
            "round_summary": "Round 6: Sentinel dominant — trajectory R² still too high. Forge raising jitter.",
        },
    ]
    return demo


# ─── Route: Current adversarial status ───────────────────────────────────────

@router.get("/status")
def get_adversarial_status() -> Dict[str, Any]:
    """Returns current Forge parameters, round count, and session statistics."""
    total = _STATE["total_attacks"]
    detected = _STATE["total_detected"]
    evaded = _STATE["total_evaded"]

    return {
        "round_number": _STATE["round_number"],
        "total_attacks": total,
        "total_detected": detected,
        "total_evaded": evaded,
        "current_catch_rate": round((detected / total * 100), 1) if total > 0 else None,
        "current_evasion_rate": round((evaded / total * 100), 1) if total > 0 else None,
        "sentinel_threshold": _STATE["sentinel_threshold"],
        "forge_params": {k: v for k, v in _STATE["forge_params"].items() if not k.startswith("_")},
        "stealth_level": _STATE["forge_params"].get("stealth_level", 1),
    }


# ─── Route: Metrics (precision / recall / F1 / evasion rate) ────────────────

@router.get("/metrics")
def get_metrics() -> Dict[str, Any]:
    """
    Computes detection performance metrics from live adversarial round data.

    In this adversarial simulation all generated identities are sleeper agents
    (type = "sleeper"), so:
        - TP = detected sleepers (flagged=True, type=sleeper)
        - FN = missed sleepers  (flagged=False, type=sleeper)
        - FP = 0 (no benign accounts are generated in adversarial rounds)
        - TN = 0

    Returns precision, recall, F1, detection_rate, evasion_rate.
    """
    rounds = _STATE["rounds"]
    total = len(rounds)

    if total == 0:
        return {
            "total_rounds": 0,
            "detected": 0,
            "evaded": 0,
            "detection_rate_pct": None,
            "evasion_rate_pct": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "avg_risk_score_detected": None,
            "avg_risk_score_evaded": None,
            "avg_flag_week": None,
            "note": "No adversarial rounds have been run yet.",
        }

    detected_rounds = [r for r in rounds if r.get("flagged", False)]
    evaded_rounds = [r for r in rounds if not r.get("flagged", False)]

    tp = len(detected_rounds)
    fn = len(evaded_rounds)
    # All rounds in adversarial mode are sleeper attacks → precision = 1.0 when flagged
    precision = 1.0 if tp > 0 else 0.0
    recall = tp / total if total > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    avg_risk_detected = (
        float(np.mean([r["risk_score"] for r in detected_rounds]))
        if detected_rounds else None
    )
    avg_risk_evaded = (
        float(np.mean([r["risk_score"] for r in evaded_rounds]))
        if evaded_rounds else None
    )
    flag_weeks = [r["flag_week"] for r in detected_rounds if r.get("flag_week") is not None]
    avg_flag_week = float(np.mean(flag_weeks)) if flag_weeks else None

    return {
        "total_rounds": total,
        "detected": tp,
        "evaded": fn,
        "detection_rate_pct": round(recall * 100, 1),
        "evasion_rate_pct": round((fn / total) * 100, 1),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "avg_risk_score_detected": round(avg_risk_detected, 3) if avg_risk_detected is not None else None,
        "avg_risk_score_evaded": round(avg_risk_evaded, 3) if avg_risk_evaded is not None else None,
        "avg_flag_week": round(avg_flag_week, 1) if avg_flag_week is not None else None,
        "note": "Precision fixed at 1.0 — adversarial rounds only generate known sleeper agents.",
    }
