"""
VeriTrace Sentinel - Layer 5
Cross-Account Behavioural Similarity Graph

Purpose:
    Identify accounts that exhibit similar behavioural patterns and
    potentially belong to the same fraud ring.

Important:
    The vectoriser intentionally preserves behavioural magnitude and
    statistical differences instead of independently L2-normalising
    every trajectory. This prevents all synthetic Forge attack accounts
    from collapsing to ~1.0 cosine similarity.
"""

import numpy as np
import networkx as nx

from sklearn.metrics.pairwise import cosine_similarity

from typing import List, Dict, Any, Optional


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MAX_WEEKS = 24


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""

    try:
        if value is None:
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def _find_strike_idx(
    timeline: List[Dict[str, Any]]
) -> Optional[int]:
    """
    Return the first fraud strike index.

    Returns None if no fraud strike exists.
    """

    for i, t in enumerate(timeline):

        if bool(t.get("fraud_strike", False)):
            return i

    return None


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0

    return float(np.mean(values))


def _safe_std(values: List[float]) -> float:
    if not values:
        return 0.0

    return float(np.std(values))


def _safe_max(values: List[float]) -> float:
    if not values:
        return 0.0

    return float(np.max(values))


def _safe_min(values: List[float]) -> float:
    if not values:
        return 0.0

    return float(np.min(values))


def _ratio(
    numerator: float,
    denominator: float
) -> float:

    if denominator <= 0:
        return 0.0

    return float(numerator / denominator)


# ============================================================
# TIMELINE FEATURE EXTRACTION
# ============================================================

def _extract_timeline_features(
    identity: Dict[str, Any],
    max_weeks: int = DEFAULT_MAX_WEEKS
) -> np.ndarray:
    """
    Extract a rich behavioural fingerprint.

    The fingerprint contains:

        1. Spend trajectory
        2. Login trajectory
        3. Transaction-count trajectory
        4. Statistical spend features
        5. Login statistics
        6. Transaction frequency
        7. Temporal gap behaviour
        8. Burst behaviour
        9. Pre/post-strike behaviour
        10. Profile-level numerical characteristics

    The vector is designed to preserve meaningful differences between
    accounts.
    """

    timeline = identity.get("timeline", [])

    if not isinstance(timeline, list):
        timeline = []

    # --------------------------------------------------------
    # Find fraud strike
    # --------------------------------------------------------

    strike_idx = _find_strike_idx(timeline)

    # Use pre-strike behaviour where possible.
    # This prevents the final fraud event from completely dominating
    # the behavioural fingerprint.
    if strike_idx is not None and strike_idx >= 3:

        incubation = timeline[:strike_idx]

    else:

        incubation = timeline[:max_weeks]

    incubation = incubation[:max_weeks]

    # --------------------------------------------------------
    # Trajectory arrays
    # --------------------------------------------------------

    spends = []
    logins = []
    transaction_counts = []
    time_values = []

    cash_out = []
    payments = []
    transfers = []
    debits = []
    cash_in = []

    for t in incubation:

        if not isinstance(t, dict):
            continue

        spend = _safe_float(
            t.get("spend", 0.0)
        )

        login_count = _safe_float(
            t.get("login_count", 0.0)
        )

        transaction_count = _safe_float(
            t.get(
                "transaction_count",
                t.get("txn_count", 0.0)
            )
        )

        spends.append(spend)
        logins.append(login_count)
        transaction_counts.append(transaction_count)

        # ----------------------------------------------------
        # Transaction types
        # ----------------------------------------------------

        tx_type = str(
            t.get(
                "transaction_type",
                t.get(
                    "type",
                    ""
                )
            )
        ).upper()

        amount = _safe_float(
            t.get("spend", t.get("amount", 0.0))
        )

        if tx_type == "CASH_OUT":
            cash_out.append(amount)

        elif tx_type == "PAYMENT":
            payments.append(amount)

        elif tx_type == "TRANSFER":
            transfers.append(amount)

        elif tx_type == "DEBIT":
            debits.append(amount)

        elif tx_type == "CASH_IN":
            cash_in.append(amount)

        # ----------------------------------------------------
        # Time
        # ----------------------------------------------------

        time_value = _safe_float(
            t.get(
                "step",
                t.get(
                    "week",
                    t.get("day", 0.0)
                )
            )
        )

        time_values.append(time_value)

    # --------------------------------------------------------
    # Pad trajectories
    # --------------------------------------------------------

    spends = spends[:max_weeks]
    logins = logins[:max_weeks]
    transaction_counts = transaction_counts[:max_weeks]

    while len(spends) < max_weeks:
        spends.append(0.0)

    while len(logins) < max_weeks:
        logins.append(0.0)

    while len(transaction_counts) < max_weeks:
        transaction_counts.append(0.0)

    spend_arr = np.asarray(
        spends,
        dtype=np.float64
    )

    login_arr = np.asarray(
        logins,
        dtype=np.float64
    )

    txn_arr = np.asarray(
        transaction_counts,
        dtype=np.float64
    )

    # --------------------------------------------------------
    # Global statistics
    # --------------------------------------------------------

    valid_spends = [
        x for x in spend_arr
        if np.isfinite(x)
    ]

    valid_logins = [
        x for x in login_arr
        if np.isfinite(x)
    ]

    valid_txns = [
        x for x in txn_arr
        if np.isfinite(x)
    ]

    total_spend = float(
        np.sum(spend_arr)
    )

    total_logins = float(
        np.sum(login_arr)
    )

    total_transactions = float(
        np.sum(txn_arr)
    )

    # --------------------------------------------------------
    # Time-gap statistics
    # --------------------------------------------------------

    if len(time_values) >= 2:

        sorted_times = np.sort(
            np.asarray(
                time_values,
                dtype=np.float64
            )
        )

        gaps = np.diff(sorted_times)

        gaps = gaps[
            np.isfinite(gaps)
        ]

    else:

        gaps = np.array(
            [],
            dtype=np.float64
        )

    avg_gap = (
        float(np.mean(gaps))
        if len(gaps) > 0
        else 0.0
    )

    std_gap = (
        float(np.std(gaps))
        if len(gaps) > 0
        else 0.0
    )

    min_gap = (
        float(np.min(gaps))
        if len(gaps) > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Burstiness
    # --------------------------------------------------------

    if len(txn_arr) > 0:

        mean_txn = float(
            np.mean(txn_arr)
        )

        std_txn = float(
            np.std(txn_arr)
        )

        burstiness = _ratio(
            std_txn,
            mean_txn + 1e-6
        )

    else:

        burstiness = 0.0

    # --------------------------------------------------------
    # Active weeks
    # --------------------------------------------------------

    active_weeks = float(
        np.sum(spend_arr > 0)
    )

    active_ratio = _ratio(
        active_weeks,
        max_weeks
    )

    # --------------------------------------------------------
    # Transaction type statistics
    # --------------------------------------------------------

    total_type_amount = (
        sum(cash_out)
        + sum(payments)
        + sum(transfers)
        + sum(debits)
        + sum(cash_in)
    )

    cash_out_ratio = _ratio(
        sum(cash_out),
        total_type_amount
    )

    payment_ratio = _ratio(
        sum(payments),
        total_type_amount
    )

    transfer_ratio = _ratio(
        sum(transfers),
        total_type_amount
    )

    debit_ratio = _ratio(
        sum(debits),
        total_type_amount
    )

    cash_in_ratio = _ratio(
        sum(cash_in),
        total_type_amount
    )

    # --------------------------------------------------------
    # Strike behaviour
    # --------------------------------------------------------

    strike_position = (
        _ratio(
            strike_idx,
            len(timeline)
        )
        if strike_idx is not None and len(timeline) > 0
        else 1.0
    )

    # --------------------------------------------------------
    # Profile information
    # --------------------------------------------------------

    profile = identity.get(
        "profile",
        {}
    )

    if not isinstance(profile, dict):
        profile = {}

    profile_features = []

    # Common numerical profile fields
    profile_keys = [
        "age",
        "account_age",
        "account_age_days",
        "avg_monthly_spend",
        "monthly_spend",
        "income",
        "risk_score",
        "credit_score",
        "login_frequency",
        "transaction_frequency",
    ]

    for key in profile_keys:

        if key in profile:

            profile_features.append(
                _safe_float(
                    profile.get(key)
                )
            )

    # Keep fixed dimensionality.
    while len(profile_features) < 6:
        profile_features.append(0.0)

    profile_features = profile_features[:6]

    # --------------------------------------------------------
    # Statistical feature block
    # --------------------------------------------------------

    stats = [
        _safe_mean(valid_spends),
        _safe_std(valid_spends),
        _safe_min(valid_spends),
        _safe_max(valid_spends),

        _safe_mean(valid_logins),
        _safe_std(valid_logins),
        _safe_max(valid_logins),

        _safe_mean(valid_txns),
        _safe_std(valid_txns),
        _safe_max(valid_txns),

        total_spend,
        total_logins,
        total_transactions,

        avg_gap,
        std_gap,
        min_gap,

        burstiness,
        active_ratio,

        cash_out_ratio,
        payment_ratio,
        transfer_ratio,
        debit_ratio,
        cash_in_ratio,

        strike_position,
    ]

    # --------------------------------------------------------
    # Combine all features
    # --------------------------------------------------------

    vector = np.concatenate(
        [
            spend_arr,
            login_arr,
            txn_arr,
            np.asarray(stats, dtype=np.float64),
            np.asarray(profile_features, dtype=np.float64),
        ]
    )

    # --------------------------------------------------------
    # Sanitize
    # --------------------------------------------------------

    vector = np.nan_to_num(
        vector,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    return vector.astype(
        np.float64
    )


# ============================================================
# PUBLIC VECTORISER
# ============================================================

def vectorize_identity(
    identity: Dict[str, Any],
    max_weeks: int = DEFAULT_MAX_WEEKS
) -> np.ndarray:
    """
    Public wrapper for behavioural fingerprint generation.
    """

    return _extract_timeline_features(
        identity,
        max_weeks=max_weeks
    )


# ============================================================
# GRAPH BUILDER
# ============================================================

def build_similarity_graph(
    identities: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
) -> Dict[str, Any]:
    """
    Build an account similarity graph.

    Parameters
    ----------
    identities:
        List of account identity dictionaries.

    similarity_threshold:
        Minimum cosine similarity required for an edge.

    Returns
    -------
    Dictionary containing:

        nodes
        edges
        total_nodes
        total_edges
        fraud_rings
    """

    # --------------------------------------------------------
    # Empty input
    # --------------------------------------------------------

    if not identities:

        return {
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
            "fraud_rings": [],
        }

    # --------------------------------------------------------
    # Build vectors
    # --------------------------------------------------------

    vectors = [
        vectorize_identity(identity)
        for identity in identities
    ]

    matrix = np.asarray(
        vectors,
        dtype=np.float64
    )

    # --------------------------------------------------------
    # Standardise each feature across accounts
    #
    # This prevents one feature with a huge magnitude from
    # dominating cosine similarity.
    # --------------------------------------------------------

    feature_mean = np.mean(
        matrix,
        axis=0
    )

    feature_std = np.std(
        matrix,
        axis=0
    )

    feature_std[
        feature_std < 1e-8
    ] = 1.0

    matrix = (
        matrix - feature_mean
    ) / feature_std

    matrix = np.nan_to_num(
        matrix,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    # --------------------------------------------------------
    # Cosine similarity
    # --------------------------------------------------------

    sim_matrix = cosine_similarity(
        matrix
    )

    # --------------------------------------------------------
    # Graph
    # --------------------------------------------------------

    G = nx.Graph()

    for ident in identities:

        account_id = str(
            ident.get(
                "id",
                ident.get(
                    "account_id",
                    ""
                )
            )
        )

        G.add_node(
            account_id,
            label=account_id,
            flagged=bool(
                ident.get(
                    "flagged",
                    False
                )
            ),
            type=str(
                ident.get(
                    "type",
                    "unknown"
                )
            ),
            risk_score=_safe_float(
                ident.get(
                    "risk_score",
                    0.0
                )
            ),
            ring_id=ident.get(
                "ring_id"
            ),
        )

    # --------------------------------------------------------
    # Add similarity edges
    # --------------------------------------------------------

    n = len(identities)

    for i in range(n):

        for j in range(i + 1, n):

            sim = float(
                sim_matrix[i, j]
            )

            if not np.isfinite(sim):
                continue

            source = str(
                identities[i].get(
                    "id",
                    identities[i].get(
                        "account_id",
                        ""
                    )
                )
            )

            target = str(
                identities[j].get(
                    "id",
                    identities[j].get(
                        "account_id",
                        ""
                    )
                )
            )

            if sim >= similarity_threshold:

                G.add_edge(
                    source,
                    target,
                    weight=round(
                        sim,
                        4
                    )
                )

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    nodes = []

    for nid, data in G.nodes(
        data=True
    ):

        nodes.append(
            {
                "id": nid,
                "label": nid,
                "flagged": bool(
                    data.get(
                        "flagged",
                        False
                    )
                ),
                "type": data.get(
                    "type",
                    "unknown"
                ),
                "risk_score": float(
                    data.get(
                        "risk_score",
                        0.0
                    )
                ),
                "ring_id": data.get(
                    "ring_id"
                ),
            }
        )

    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

    edges = []

    for u, v, data in G.edges(
        data=True
    ):

        edges.append(
            {
                "source": u,
                "target": v,
                "weight": float(
                    data.get(
                        "weight",
                        0.0
                    )
                ),
            }
        )

    # --------------------------------------------------------
    # Fraud ring detection
    # --------------------------------------------------------

    fraud_rings = []

    components = nx.connected_components(
        G
    )

    ring_counter = 1

    for component in components:

        members = list(
            component
        )

        if len(members) < 2:
            continue

        flagged_members = [
            m
            for m in members
            if G.nodes[m].get(
                "flagged",
                False
            )
        ]

        ring_ids = {
            G.nodes[m].get(
                "ring_id"
            )
            for m in members
            if G.nodes[m].get(
                "ring_id"
            )
        }

        # A component becomes a fraud ring candidate when
        # it contains multiple flagged accounts.
        if len(flagged_members) >= 2:

            fraud_rings.append(
                {
                    "ring_id": (
                        next(
                            iter(ring_ids)
                        )
                        if ring_ids
                        else f"RING_{ring_counter:03d}"
                    ),
                    "member_ids": members,
                    "size": len(members),
                    "flagged_count": len(
                        flagged_members
                    ),
                }
            )

            ring_counter += 1

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "fraud_rings": fraud_rings,
    }