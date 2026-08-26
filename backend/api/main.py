from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import time

from forge.generator import generate_timeline, generate_batch
from sentinel.trajectory_model import score_trajectory
from sentinel.similarity_graph import build_similarity_graph

app = FastAPI(
    title="VeriTrace Sentinel API",
    description="Adversarial AI Defense against GenAI-Scripted Synthetic Identity & Sleeper Agent Attacks",
    version="1.0.0"
)

# Enable CORS for frontend Vite dev server (and all origins for seamless local demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database of generated identities and timelines
IDENTITIES_STORE: Dict[str, Dict[str, Any]] = {}

class GenerateRequest(BaseModel):
    identity_type: Optional[str] = Field(None, description="'sleeper' or 'benign' or None for 50/50 randomized")
    weeks: Optional[int] = Field(24, description="Number of weeks in timeline (default 24)")
    ring_id: Optional[str] = Field(None, description="Optional fraud ring tag to cluster with")

def process_and_store_identity(raw_identity: Dict[str, Any]) -> Dict[str, Any]:
    """Scores trajectory and stores identity in the in-memory registry."""
    verdict = score_trajectory(raw_identity["timeline"])
    
    record = {
        "id": raw_identity["id"],
        "type": raw_identity["type"],
        "ring_id": raw_identity.get("ring_id"),
        "weeks_count": raw_identity.get("weeks_count", len(raw_identity["timeline"])),
        "timeline": raw_identity["timeline"],
        "flagged": verdict["flagged"],
        "risk_score": verdict["risk_score"],
        "flag_week": verdict["flag_week"],
        "features": verdict["features"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    IDENTITIES_STORE[record["id"]] = record
    return record

@app.on_event("startup")
def seed_initial_identities():
    """Seeds the system with realistic initial identities and a sleeper fraud ring cluster."""
    if not IDENTITIES_STORE:
        # Seed a 10-identity batch containing a coordinated 4-node sleeper ring
        initial_batch = generate_batch(count=10, sleeper_ratio=0.5)
        for ident in initial_batch:
            process_and_store_identity(ident)
        print(f"[VeriTrace] Startup seed complete. {len(IDENTITIES_STORE)} identities loaded.")

@app.get("/")
def root():
    return {
        "system": "VeriTrace Sentinel API",
        "status": "active",
        "identities_monitored": len(IDENTITIES_STORE),
        "docs_url": "/docs"
    }

@app.post("/forge/generate")
def generate_identity(req: Optional[GenerateRequest] = None):
    """
    Generates a synthetic identity's 6-month weekly behavioral timeline.
    Randomly injects a fraud strike for ~50% (sleeper type) and returns
    verdict, risk score, and flag week.
    """
    itype = req.identity_type if req else None
    weeks = req.weeks if req and req.weeks else 24
    ring_id = req.ring_id if req else None
    
    raw = generate_timeline(identity_type=itype, weeks=weeks, ring_id=ring_id)
    record = process_and_store_identity(raw)
    
    return {
        "id": record["id"],
        "type": record["type"],
        "ring_id": record["ring_id"],
        "timeline": record["timeline"],
        "flagged": record["flagged"],
        "risk_score": record["risk_score"],
        "flag_week": record["flag_week"],
        "features": record["features"]
    }

@app.get("/sentinel/history")
def get_history():
    """
    Returns list of all previously generated identities with their verdicts.
    Ordered with newest first.
    """
    records = list(IDENTITIES_STORE.values())
    # Return sorted by newest
    records.reverse()
    
    summary = []
    for r in records:
        summary.append({
            "id": r["id"],
            "type": r["type"],
            "flagged": r["flagged"],
            "risk_score": r["risk_score"],
            "flag_week": r["flag_week"],
            "ring_id": r.get("ring_id"),
            "weeks_count": r.get("weeks_count", 24),
            "created_at": r.get("created_at")
        })
    return summary

@app.get("/sentinel/timeline/{identity_id}")
def get_timeline(identity_id: str):
    """
    Returns structured timeline for an identity:
    {id, weeks: [...], spend: [...], logins: [...], flag_week: int, type: str, flagged: bool, ...}
    """
    record = IDENTITIES_STORE.get(identity_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Identity {identity_id} not found")
        
    weeks = [t["week"] for t in record["timeline"]]
    spend = [t["spend"] for t in record["timeline"]]
    logins = [t["login_count"] for t in record["timeline"]]
    strikes = [t.get("fraud_strike", False) for t in record["timeline"]]
    
    return {
        "id": record["id"],
        "type": record["type"],
        "flagged": record["flagged"],
        "risk_score": record["risk_score"],
        "flag_week": record["flag_week"],
        "features": record.get("features", {}),
        "ring_id": record.get("ring_id"),
        "weeks": weeks,
        "spend": spend,
        "logins": logins,
        "fraud_strikes": strikes,
        "timeline": record["timeline"]
    }

@app.get("/sentinel/rounds")
def get_rounds():
    """
    Returns simulated round-by-round catch rate data across 10 adversarial rounds.
    Demonstrates the arms race:
    - Round 1-3: Baseline defense catch rate ~78-85%
    - Round 4-6: GenAI adversaries adapt prompt templates adding subtle jitter -> Catch rate dips to ~54%
    - Round 7-10: VeriTrace Sentinel adapts Trajectory Monotonicity + Cosine Similarity -> Catch rate recovers to 96%
    """
    rounds_data = [
        {"round": 1, "catch_rate": 84.0, "stage": "Baseline Rule Engine", "adversary_strategy": "Naïve linear spend script"},
        {"round": 2, "catch_rate": 88.5, "stage": "Heuristic Filtering", "adversary_strategy": "Fixed weekly spend ramps"},
        {"round": 3, "catch_rate": 81.0, "stage": "Early Detection", "adversary_strategy": "Multi-account batch generator"},
        {"round": 4, "catch_rate": 62.5, "stage": "Adversary Evasion Wave 1", "adversary_strategy": "GenAI LLM agent adds login noise"},
        {"round": 5, "catch_rate": 54.0, "stage": "Adversary Evasion Wave 2", "adversary_strategy": "Sub-threshold random spend jitter"},
        {"round": 6, "catch_rate": 58.5, "stage": "Sentinel Model Retraining", "adversary_strategy": "Dynamic prompt templating"},
        {"round": 7, "catch_rate": 74.0, "stage": "Trajectory R² Forensics", "adversary_strategy": "Staggered incubation period"},
        {"round": 8, "catch_rate": 86.5, "stage": "Cosine Similarity Clustering", "adversary_strategy": "Sleeper fraud ring coordination"},
        {"round": 9, "catch_rate": 93.0, "stage": "Multi-Modal Graph Sentinel", "adversary_strategy": "Coordinated bust-out attempt"},
        {"round": 10, "catch_rate": 96.8, "stage": "Autonomous Sentinel Equilibrium", "adversary_strategy": "Zero-day prompt variations intercepted"}
    ]
    return rounds_data

@app.get("/sentinel/graph")
def get_graph(threshold: float = Query(0.88, ge=0.5, le=1.0)):
    """
    Returns NetworkX cosine similarity graph of generated identities.
    Nodes are colored by flagged status, and clustered high-similarity edges reveal fraud rings.
    """
    identities_list = list(IDENTITIES_STORE.values())
    return build_similarity_graph(identities_list, similarity_threshold=threshold)
