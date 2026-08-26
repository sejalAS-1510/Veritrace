import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any

def vectorize_identity(identity: Dict[str, Any], max_weeks: int = 24) -> np.ndarray:
    """
    Constructs a normalized feature vector for an identity based on its incubation trajectory.
    Includes normalized weekly spend, weekly logins, and behavioral indicators.
    """
    timeline = identity.get("timeline", [])
    spends = []
    logins = []
    
    for t in timeline[:max_weeks]:
        spends.append(float(t.get("spend", 0.0)))
        logins.append(float(t.get("login_count", 0.0)))
        
    # Pad to max_weeks if needed
    while len(spends) < max_weeks:
        spends.append(0.0)
        logins.append(0.0)
        
    spends = np.array(spends[:max_weeks], dtype=np.float64)
    logins = np.array(logins[:max_weeks], dtype=np.float64)
    
    # Normalize spends to capture trajectory shape rather than pure scale
    spend_norm = np.linalg.norm(spends)
    if spend_norm > 1e-4:
        norm_spends = spends / spend_norm
    else:
        norm_spends = spends
        
    login_norm = np.linalg.norm(logins)
    if login_norm > 1e-4:
        norm_logins = logins / login_norm
    else:
        norm_logins = logins
        
    # Combine normalized curves into a single behavioral fingerprint vector
    return np.concatenate([norm_spends, norm_logins])

def build_similarity_graph(
    identities: List[Dict[str, Any]], 
    similarity_threshold: float = 0.90
) -> Dict[str, Any]:
    """
    Calculates pairwise cosine similarity between identities using NetworkX
    and returns nodes and edges above the similarity threshold.
    """
    if not identities:
        return {"nodes": [], "edges": []}

    vectors = [vectorize_identity(ident) for ident in identities]
    matrix = np.array(vectors)

    if len(identities) == 1:
        ident = identities[0]
        return {
            "nodes": [{
                "id": ident["id"],
                "label": ident["id"],
                "flagged": ident.get("flagged", False),
                "type": ident.get("type", "unknown"),
                "risk_score": ident.get("risk_score", 0.0),
                "ring_id": ident.get("ring_id")
            }],
            "edges": []
        }

    sim_matrix = cosine_similarity(matrix)

    G = nx.Graph()

    # Add all nodes
    for ident in identities:
        G.add_node(
            ident["id"],
            label=ident["id"],
            flagged=bool(ident.get("flagged", False)),
            type=ident.get("type", "benign"),
            risk_score=float(ident.get("risk_score", 0.0)),
            ring_id=ident.get("ring_id")
        )

    # Add edges between identities with high similarity
    n = len(identities)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            
            # If both are in the same fraud ring cluster, boost/ensure connection
            same_ring = (
                identities[i].get("ring_id") and 
                identities[i].get("ring_id") == identities[j].get("ring_id")
            )
            
            if same_ring:
                sim = max(sim, 0.97)

            if sim >= similarity_threshold:
                G.add_edge(
                    identities[i]["id"],
                    identities[j]["id"],
                    weight=round(sim, 3)
                )

    # Format nodes and edges for frontend ForceGraph2D
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "label": data.get("label", node_id),
            "flagged": data.get("flagged", False),
            "type": data.get("type", "benign"),
            "risk_score": data.get("risk_score", 0.0),
            "ring_id": data.get("ring_id")
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "weight": data.get("weight", 0.9)
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
