"""
VeriTrace Sentinel — Main FastAPI Application
Member 3: Backend / Adversarial Engine

Endpoint map
------------
GET  /                          Health check + stats
POST /forge/generate            Generate one identity (sleeper or benign)
POST /forge/batch               Generate a batch (with optional fraud ring)
POST /sentinel/analyze          Analyze an externally-supplied timeline
GET  /sentinel/history          All evaluated identities, newest first
GET  /sentinel/timeline/{id}    Full weekly timeline for one identity
GET  /sentinel/graph            Cosine-similarity fraud-ring graph
GET  /accounts                  Alias for /sentinel/history (broader label)
GET  /accounts/{id}             Alias for /sentinel/timeline/{id}
GET  /attacks                   All identities where type=sleeper
GET  /metrics                   Aggregate detection metrics across all identities

Adversarial loop (via adversarial router)
POST /adversarial/run
POST /adversarial/reset
POST /adversarial/feedback
GET  /adversarial/rounds
GET  /adversarial/status
GET  /adversarial/metrics
"""

import time
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.adversarial import router as adversarial_router, _STATE as ADV_STATE
from forge.generator import generate_timeline, generate_batch
from sentinel.trajectory_model import score_trajectory
from sentinel.similarity_graph import build_similarity_graph

# ─── App setup ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="VeriTrace Sentinel API",
    description=(
        "Adversarial AI Defence against GenAI-Scripted Synthetic Identity "
        "& Sleeper Agent Attacks. Forge vs Sentinel arms-race simulation."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(adversarial_router)

# ─── In-memory identity store ─────────────────────────────────────────────────
# Key: identity_id → full record dict

IDENTITIES_STORE: Dict[str, Dict[str, Any]] = {}


# ─── Pydantic models ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    identity_type: Optional[str] = Field(
        None, description="'sleeper' | 'benign' | null for 50/50 random"
    )
    weeks: int = Field(24, ge=4, le=52, description="Timeline length in weeks")
    ring_id: Optional[str] = Field(
        None, description="Tag to cluster this identity into a fraud ring"
    )


class BatchRequest(BaseModel):
    count: int = Field(10, ge=2, le=100, description="Number of identities to generate")
    sleeper_ratio: float = Field(
        0.5, ge=0.0, le=1.0, description="Fraction that are sleeper agents"
    )


class AnalyzeRequest(BaseModel):
    timeline: List[Dict[str, Any]] = Field(
        ..., description="List of weekly event dicts (must include 'week', 'spend', 'login_count')"
    )
    identity_id: Optional[str] = Field(None, description="Optional ID to label this analysis")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _score_and_store(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs Sentinel scoring on a raw Forge identity and saves to IDENTITIES_STORE.
    Returns the full enriched record.
    """
    verdict = score_trajectory(raw["timeline"])

    record: Dict[str, Any] = {
        "id": raw["id"],
        "type": raw["type"],
        "ring_id": raw.get("ring_id"),
        "weeks_count": raw.get("weeks_count", len(raw["timeline"])),
        "timeline": raw["timeline"],
        # Sentinel output
        "flagged": verdict["flagged"],
        "risk_score": verdict["risk_score"],
        "risk_score_pct": round(verdict["risk_score"] * 100, 1),
        "flag_week": verdict["flag_week"],
        "features": verdict["features"],
        "risk_breakdown": verdict.get("risk_breakdown", {}),
        # Explainability: human-readable reasons
        "detection_reasons": _build_reasons(verdict),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    IDENTITIES_STORE[record["id"]] = record
    return record


def _build_reasons(verdict: Dict[str, Any]) -> List[str]:
    """
    Converts numeric feature scores into human-readable detection reasons
    for the explainability panel in the dashboard.
    """
    reasons: List[str] = []
    f = verdict.get("features", {})
    bd = verdict.get("risk_breakdown", {})

    if f.get("spend_smoothness", 0) > 0.70:
        reasons.append(
            f"Spend linearity (R²={f['spend_smoothness']:.2f}) — "
            "incubation spend follows an unnatural straight-line ramp"
        )
    if f.get("spend_monotonicity", 0) > 0.75:
        reasons.append(
            f"Spend monotonicity ({f['spend_monotonicity']*100:.0f}% non-decreasing) — "
            "real humans have spending dips; this account never does"
        )
    if f.get("login_regularity", 0) > 0.60:
        reasons.append(
            f"Login regularity (score={f['login_regularity']:.2f}) — "
            "sessions occur at near-identical frequency every week"
        )
    if f.get("variance_score", 1) < 0.20:
        reasons.append(
            f"Low spending variance (CV={f['variance_score']:.3f}) — "
            "spend distribution is unnaturally tight for a human consumer"
        )
    if f.get("bust_out_ratio", 0) > 0.40:
        reasons.append(
            f"Terminal transaction anomaly (bust-out ratio={f['bust_out_ratio']:.2f}) — "
            "final spend deviates far from account's own baseline"
        )
    if bd.get("transaction_anomaly", 0) > 0.75:
        reasons.append(
            f"Transaction z-score anomaly ({bd['transaction_anomaly']:.2f}) — "
            "final event is a statistical outlier vs this account's history"
        )
    if not reasons and verdict.get("flagged"):
        reasons.append("Combined multi-signal trajectory anomaly exceeded threshold")

    return reasons


def _summary_record(r: Dict[str, Any]) -> Dict[str, Any]:
    """Strips the full timeline from a record for list responses."""
    return {
        "id": r["id"],
        "type": r["type"],
        "flagged": r["flagged"],
        "risk_score": r["risk_score"],
        "risk_score_pct": r.get("risk_score_pct", round(r["risk_score"] * 100, 1)),
        "flag_week": r["flag_week"],
        "ring_id": r.get("ring_id"),
        "weeks_count": r.get("weeks_count", 24),
        "detection_reasons": r.get("detection_reasons", []),
        "created_at": r.get("created_at"),
    }


# ─── Startup seed ─────────────────────────────────────────────────────────────

@app.on_event("startup")
def seed_initial_identities() -> None:
    """
    Seeds 10 identities on startup: ~4 in a coordinated ring, rest random.
    Gives the frontend graph and history something to display immediately.
    """
    if not IDENTITIES_STORE:
        batch = generate_batch(count=10, sleeper_ratio=0.5)
        for raw in batch:
            _score_and_store(raw)
        print(f"[VeriTrace] Seeded {len(IDENTITIES_STORE)} identities on startup.")


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/", tags=["system"])
def root() -> Dict[str, Any]:
    total = len(IDENTITIES_STORE)
    flagged = sum(1 for r in IDENTITIES_STORE.values() if r["flagged"])
    return {
        "system": "VeriTrace Sentinel API",
        "version": "2.0.0",
        "status": "active",
        "identities_monitored": total,
        "sleeper_agents_flagged": flagged,
        "adversarial_rounds_run": ADV_STATE["round_number"],
        "docs_url": "/docs",
    }


# ─── Forge endpoints ──────────────────────────────────────────────────────────

@app.post("/forge/generate", tags=["forge"])
def generate_identity(req: GenerateRequest) -> Dict[str, Any]:
    """
    Generates one synthetic identity (sleeper or benign) and immediately
    scores it through Sentinel. Returns the full record including timeline,
    risk score, flag week, features, and detection reasons.
    """
    raw = generate_timeline(
        identity_type=req.identity_type,
        weeks=req.weeks,
        ring_id=req.ring_id,
    )
    record = _score_and_store(raw)

    return {
        "id": record["id"],
        "type": record["type"],
        "ring_id": record["ring_id"],
        "weeks_count": record["weeks_count"],
        "timeline": record["timeline"],
        "flagged": record["flagged"],
        "risk_score": record["risk_score"],
        "risk_score_pct": record["risk_score_pct"],
        "flag_week": record["flag_week"],
        "features": record["features"],
        "risk_breakdown": record["risk_breakdown"],
        "detection_reasons": record["detection_reasons"],
    }


@app.post("/forge/batch", tags=["forge"])
def generate_identity_batch(req: BatchRequest) -> Dict[str, Any]:
    """
    Generates a batch of identities. Always includes one coordinated fraud
    ring cluster (3–4 sleepers sharing identical behavioural parameters).

    Returns summary list + ring info without full timelines (use
    GET /sentinel/timeline/{id} for individual timelines).
    """
    batch = generate_batch(count=req.count, sleeper_ratio=req.sleeper_ratio)
    records = [_score_and_store(raw) for raw in batch]

    ring_ids = {r["ring_id"] for r in records if r.get("ring_id")}
    return {
        "generated": len(records),
        "sleepers": sum(1 for r in records if r["type"] == "sleeper"),
        "benign": sum(1 for r in records if r["type"] == "benign"),
        "flagged": sum(1 for r in records if r["flagged"]),
        "fraud_rings_seeded": list(ring_ids),
        "identities": [_summary_record(r) for r in records],
    }


# ─── Sentinel endpoints ───────────────────────────────────────────────────────

@app.post("/sentinel/analyze", tags=["sentinel"])
def analyze_timeline(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Scores an externally-supplied timeline through Sentinel.
    Does NOT require a Forge-generated identity — accepts any timeline dict.
    Useful for Member 1's Forge to push raw timelines for evaluation.

    The identity is stored in IDENTITIES_STORE under the provided id
    (or a generated one) and appears in history + graph.
    """
    import uuid as _uuid

    identity_id = req.identity_id or f"EXT-{_uuid.uuid4().hex[:8].upper()}"
    raw = {
        "id": identity_id,
        "type": "unknown",
        "ring_id": None,
        "timeline": req.timeline,
        "weeks_count": len(req.timeline),
    }
    record = _score_and_store(raw)

    return {
        "id": record["id"],
        "flagged": record["flagged"],
        "risk_score": record["risk_score"],
        "risk_score_pct": record["risk_score_pct"],
        "flag_week": record["flag_week"],
        "features": record["features"],
        "risk_breakdown": record["risk_breakdown"],
        "detection_reasons": record["detection_reasons"],
    }


@app.get("/sentinel/history", tags=["sentinel"])
def get_history(
    limit: int = Query(100, ge=1, le=500),
    type_filter: Optional[str] = Query(None, description="'sleeper' | 'benign' | 'unknown'"),
    flagged_only: bool = Query(False),
) -> List[Dict[str, Any]]:
    """
    Returns evaluated identities, newest first.
    Supports optional filtering by type and flagged status.
    """
    records = list(reversed(list(IDENTITIES_STORE.values())))

    if type_filter:
        records = [r for r in records if r.get("type") == type_filter]
    if flagged_only:
        records = [r for r in records if r.get("flagged")]

    return [_summary_record(r) for r in records[:limit]]


@app.get("/sentinel/timeline/{identity_id}", tags=["sentinel"])
def get_timeline(identity_id: str) -> Dict[str, Any]:
    """
    Returns the full weekly timeline for a single identity plus all
    Sentinel verdict fields. Used by the Timeline Replay tab.
    """
    record = IDENTITIES_STORE.get(identity_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Identity '{identity_id}' not found")

    tl = record["timeline"]
    return {
        "id": record["id"],
        "type": record["type"],
        "ring_id": record.get("ring_id"),
        "weeks_count": record.get("weeks_count", len(tl)),
        "flagged": record["flagged"],
        "risk_score": record["risk_score"],
        "risk_score_pct": record.get("risk_score_pct", round(record["risk_score"] * 100, 1)),
        "flag_week": record["flag_week"],
        "features": record.get("features", {}),
        "risk_breakdown": record.get("risk_breakdown", {}),
        "detection_reasons": record.get("detection_reasons", []),
        # Flat arrays for chart rendering
        "weeks": [t["week"] for t in tl],
        "spend": [t["spend"] for t in tl],
        "logins": [t["login_count"] for t in tl],
        "fraud_strikes": [t.get("fraud_strike", False) for t in tl],
        "new_devices": [t.get("new_device", False) for t in tl],
        "location_changes": [t.get("location_change", False) for t in tl],
        "bills_paid": [t.get("bill_paid_on_time", True) for t in tl],
        # Full timeline for detailed inspection
        "timeline": tl,
    }


@app.get("/sentinel/graph", tags=["sentinel"])
def get_graph(
    threshold: float = Query(0.88, ge=0.50, le=1.0, description="Cosine similarity threshold"),
) -> Dict[str, Any]:
    """
    Builds and returns the cosine-similarity fraud-ring graph from all
    stored identities. Edges appear where similarity >= threshold.

    Returns nodes, edges, and detected fraud_rings for the frontend graph tab.
    """
    identities = list(IDENTITIES_STORE.values())
    return build_similarity_graph(identities, similarity_threshold=threshold)


# ─── Convenience alias endpoints ─────────────────────────────────────────────

@app.get("/accounts", tags=["accounts"])
def list_accounts(
    limit: int = Query(100, ge=1, le=500),
    type_filter: Optional[str] = Query(None),
    flagged_only: bool = Query(False),
) -> List[Dict[str, Any]]:
    """Alias for GET /sentinel/history. Broader label for the project spec."""
    return get_history(limit=limit, type_filter=type_filter, flagged_only=flagged_only)


@app.get("/accounts/{identity_id}", tags=["accounts"])
def get_account(identity_id: str) -> Dict[str, Any]:
    """Alias for GET /sentinel/timeline/{id}."""
    return get_timeline(identity_id)


@app.get("/attacks", tags=["accounts"])
def list_attacks(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    """
    Returns all sleeper-type identities (the 'attacks') with their
    Sentinel verdict. Ordered by risk score descending.
    """
    attacks = [
        r for r in IDENTITIES_STORE.values()
        if r.get("type") == "sleeper"
    ]
    attacks.sort(key=lambda r: r["risk_score"], reverse=True)
    return [_summary_record(r) for r in attacks[:limit]]


# ─── Aggregate metrics endpoint ───────────────────────────────────────────────

@app.get("/metrics", tags=["metrics"])
def get_aggregate_metrics() -> Dict[str, Any]:
    """
    Computes detection performance across ALL identities in the store
    (Forge-generated + adversarial + externally analyzed).

    Returns precision, recall, F1, false-positive rate, and per-type counts.
    These are the real numbers the judges will ask about.
    """
    all_records = list(IDENTITIES_STORE.values())
    total = len(all_records)

    if total == 0:
        return {"total": 0, "note": "No identities evaluated yet."}

    sleepers = [r for r in all_records if r.get("type") == "sleeper"]
    benign = [r for r in all_records if r.get("type") == "benign"]

    # True positives: sleepers correctly flagged
    tp = sum(1 for r in sleepers if r["flagged"])
    # False negatives: sleepers missed
    fn = sum(1 for r in sleepers if not r["flagged"])
    # False positives: benign incorrectly flagged
    fp = sum(1 for r in benign if r["flagged"])
    # True negatives: benign correctly cleared
    tn = sum(1 for r in benign if not r["flagged"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision and recall
        else None
    )
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else None
    detection_rate = tp / len(sleepers) if sleepers else None
    evasion_rate = fn / len(sleepers) if sleepers else None

    # Risk score distributions
    sleeper_risks = [r["risk_score"] for r in sleepers]
    benign_risks = [r["risk_score"] for r in benign]

    flag_weeks = [r["flag_week"] for r in sleepers if r.get("flag_week") is not None]

    return {
        "total_identities": total,
        "total_sleepers": len(sleepers),
        "total_benign": len(benign),
        # Core metrics
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1_score": round(f1, 3) if f1 is not None else None,
        "false_positive_rate_pct": round(false_positive_rate * 100, 1) if false_positive_rate is not None else None,
        "detection_rate_pct": round(detection_rate * 100, 1) if detection_rate is not None else None,
        "evasion_rate_pct": round(evasion_rate * 100, 1) if evasion_rate is not None else None,
        # Risk score stats
        "avg_risk_sleeper": round(float(np.mean(sleeper_risks)), 3) if sleeper_risks else None,
        "avg_risk_benign": round(float(np.mean(benign_risks)), 3) if benign_risks else None,
        "max_risk_benign": round(float(np.max(benign_risks)), 3) if benign_risks else None,
        # Early warning
        "avg_flag_week": round(float(np.mean(flag_weeks)), 1) if flag_weeks else None,
        "earliest_flag_week": int(min(flag_weeks)) if flag_weeks else None,
        # Adversarial round stats (from live adversarial session)
        "adversarial_rounds": ADV_STATE["round_number"],
        "adversarial_detected": ADV_STATE["total_detected"],
        "adversarial_evaded": ADV_STATE["total_evaded"],
    }


# ─── Legacy endpoint (kept for backwards compat with existing frontend) ───────

@app.get("/sentinel/rounds", tags=["sentinel"])
def get_legacy_rounds() -> List[Dict[str, Any]]:
    """
    Returns adversarial round history.
    Delegates to /adversarial/rounds — kept so the existing ArmsRaceChart
    component continues to work without changes.
    """
    from api.adversarial import get_adversarial_rounds
    return get_adversarial_rounds()
