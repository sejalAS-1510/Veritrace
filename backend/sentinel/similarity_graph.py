"""
VeriTrace Sentinel — Cross-Account Fraud Ring Graph
Member 2 owns the vectoriser; Member 3 owns the API endpoint.

Key design decision: vectorise using INCUBATION spend only (exclude the
bust-out week) so legitimate cluster similarity isn't blown apart by the
surge in one account's final transaction.
"""

import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional


def _find_strike_idx(timeline: List[Dict[str, Any]]) -> Optional[int]:
    """Returns the index of the first fraud_strike week, or None."""
    for i, t in enumerate(timeline):
        if t.get("fraud_strike", False):
            return i
    return None


def vectorize_identity(identity: Dict[str, Any], max_weeks: int = 24) -> np.ndarray:
    """
    Constructs a normalised behavioural fingerprint vector from the
    INCUBATION portion of a timeline (pre-strike weeks only).

    Including the bust-out spend would dominate the cosine distance and
    prevent real fraud-ring clusters from forming. We exclude it.

    Vector = [normalised_incubation_spend × 24, normalised_logins × 24]
    """
    timeline = identity.get("timeline", [])
    strike_idx = _find_strike_idx(timeline)

    # Use only incubation data; fall back to full timeline if no strike
    if strike_idx is not None and strike_idx >= 3:
        incubation = timeline[:strike_idx]
    else:
        incubation = timeline[:max_weeks]

    spends: List[float] = []
    logins: List[float] = []
    for t in incubation[:max_weeks]:
        spends.append(float(t.get("spend", 0.0)))
        logins.append(float(t.get("login_count", 0.0)))

    # Pad to max_weeks
    while len(spends) < max_weeks:
        spends.append(0.0)
        logins.append(0.0)

    arr_spends = np.array(spends[:max_weeks], dtype=np.float64)
    arr_logins = np.array(logins[:max_weeks], dtype=np.float64)

    # L2-normalise each half so cosine similarity captures trajectory SHAPE
    spend_norm = np.linalg.norm(arr_spends)
    norm_spends = arr_spends / spend_norm if spend_norm > 1e-4 else arr_spends

    login_norm = np.linalg.norm(arr_logins)
    norm_logins = arr_logins / login_norm if login_norm > 1e-4 else arr_logins

    return np.concatenate([norm_spends, norm_logins])


def build_similarity_graph(
    identities: List[Dict[str, Any]],
    similarity_threshold: float = 0.90,
) -> Dict[str, Any]:
    """
    Computes pairwise cosine similarity on behavioural fingerprint vectors,
    builds a NetworkX graph, and returns nodes + edges for the frontend.

    Edges appear only when similarity >= threshold.
    Accounts in the same fraud ring (same ring_id) always get an edge
    (similarity boosted to 0.97) regardless of threshold.

    Returns
    -------
    {
        nodes: [{id, label, flagged, type, risk_score, ring_id}],
        edges: [{source, target, weight}],
        total_nodes, total_edges,
        fraud_rings: [{ring_id, member_ids, size}]
    }
    """
    if not identities:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "fraud_rings": []}

    if len(identities) == 1:
        ident = identities[0]
        return {
            "nodes": [{
                "id": ident["id"],
                "label": ident["id"],
                "flagged": bool(ident.get("flagged", False)),
                "type": ident.get("type", "unknown"),
                "risk_score": float(ident.get("risk_score", 0.0)),
                "ring_id": ident.get("ring_id"),
            }],
            "edges": [],
            "total_nodes": 1,
            "total_edges": 0,
            "fraud_rings": [],
        }

    # Build feature matrix
    vectors = [vectorize_identity(ident) for ident in identities]
    matrix = np.array(vectors)
    sim_matrix = cosine_similarity(matrix)

    G = nx.Graph()

    for ident in identities:
        G.add_node(
            ident["id"],
            label=ident["id"],
            flagged=bool(ident.get("flagged", False)),
            type=str(ident.get("type", "benign")),
            risk_score=float(ident.get("risk_score", 0.0)),
            ring_id=ident.get("ring_id"),
        )

    n = len(identities)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])

            same_ring = (
                identities[i].get("ring_id")
                and identities[i].get("ring_id") == identities[j].get("ring_id")
            )
            if same_ring:
                sim = max(sim, 0.97)

            if sim >= similarity_threshold:
                G.add_edge(identities[i]["id"], identities[j]["id"], weight=round(sim, 4))

    nodes = [
        {
            "id": nid,
            "label": nid,
            "flagged": data.get("flagged", False),
            "type": data.get("type", "benign"),
            "risk_score": data.get("risk_score", 0.0),
            "ring_id": data.get("ring_id"),
        }
        for nid, data in G.nodes(data=True)
    ]

    edges = [
        {"source": u, "target": v, "weight": data.get("weight", 0.9)}
        for u, v, data in G.edges(data=True)
    ]

    # Summarise fraud rings (connected components with ≥2 flagged sleeper nodes)
    fraud_rings = []
    for component in nx.connected_components(G):
        members = list(component)
        if len(members) < 2:
            continue
        ring_ids = {G.nodes[m].get("ring_id") for m in members if G.nodes[m].get("ring_id")}
        flagged_members = [m for m in members if G.nodes[m].get("flagged")]
        if len(flagged_members) >= 2:
            fraud_rings.append({
                "ring_id": next(iter(ring_ids), None),
                "member_ids": members,
                "size": len(members),
                "flagged_count": len(flagged_members),
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "fraud_rings": fraud_rings,
    }
