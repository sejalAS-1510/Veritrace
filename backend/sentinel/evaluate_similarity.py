"""
VeriTrace Sentinel - Layer 5
Cross-Account Similarity Evaluation

Evaluates the behavioural similarity graph generated from Forge
identity/timeline data.

Important:
    batch_attack_timeline.json contains attack identities only.
    Therefore conventional binary precision/recall against normal
    accounts is NOT used.

Instead this script evaluates:

    - similarity distribution
    - graph density
    - number of connected components
    - multi-account clusters
    - largest cluster
    - average degree
    - fraud-ring candidates
"""

import json
import os

import numpy as np
import pandas as pd
import networkx as nx

from typing import Dict, Any, List

from similarity_graph import (
    vectorize_identity,
    build_similarity_graph,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FORGE_PATH = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "generated",
    "batch_attack_timeline.json",
)

RESULTS_DIR = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "results",
)

OUTPUT_PATH = os.path.join(
    RESULTS_DIR,
    "forge_similarity_graph.json",
)


# ============================================================
# SETTINGS
# ============================================================

THRESHOLDS = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.92,
    0.95,
]


# ============================================================
# LOAD FORGE
# ============================================================

def load_forge() -> List[Dict[str, Any]]:

    print("=" * 60)
    print("LOADING FORGE DATA")
    print("=" * 60)

    print(
        f"Loading Forge identity data:\n{FORGE_PATH}"
    )

    if not os.path.exists(
        FORGE_PATH
    ):

        raise FileNotFoundError(
            f"Forge file not found:\n{FORGE_PATH}"
        )

    with open(
        FORGE_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    # --------------------------------------------------------
    # Handle possible wrappers
    # --------------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        for key in [
            "identities",
            "accounts",
            "data",
            "results",
        ]:

            if key in data:

                data = data[key]
                break

    if not isinstance(
        data,
        list
    ):

        raise ValueError(
            "Forge identity data must be a list."
        )

    print(
        f"Forge identities loaded: {len(data)}"
    )

    if data:

        print(
            "\nForge identity fields:"
        )

        print(
            list(data[0].keys())
        )

    return data


# ============================================================
# ACCOUNT GROUND TRUTH
# ============================================================

def build_ground_truth(
    identities: List[Dict[str, Any]]
) -> pd.DataFrame:

    print("\n" + "=" * 60)
    print("BUILDING ACCOUNT-LEVEL GROUND TRUTH")
    print("=" * 60)

    rows = []

    for identity in identities:

        account_id = identity.get(
            "account_id",
            identity.get(
                "id",
                ""
            )
        )

        timeline = identity.get(
            "timeline",
            []
        )

        actual_attack = 0

        # ----------------------------------------------------
        # Look for explicit attack markers
        # ----------------------------------------------------

        if isinstance(
            timeline,
            list
        ):

            for event in timeline:

                if not isinstance(
                    event,
                    dict
                ):
                    continue

                if bool(
                    event.get(
                        "fraud_strike",
                        False
                    )
                ):

                    actual_attack = 1
                    break

                if bool(
                    event.get(
                        "is_attack",
                        False
                    )
                ):

                    actual_attack = 1
                    break

        # ----------------------------------------------------
        # Also inspect identity-level fields
        # ----------------------------------------------------

        if bool(
            identity.get(
                "flagged",
                False
            )
        ):

            actual_attack = 1

        if identity.get(
            "attack_type"
        ):

            actual_attack = 1

        rows.append(
            {
                "account_id": account_id,
                "actual_attack": actual_attack,
            }
        )

    df = pd.DataFrame(
        rows
    )

    print(
        "\nAccount labels:"
    )

    print(
        df["actual_attack"].value_counts()
    )

    fraud_accounts = int(
        df["actual_attack"].sum()
    )

    normal_accounts = int(
        len(df) - fraud_accounts
    )

    print(
        f"\nFraud accounts: {fraud_accounts}"
    )

    print(
        f"Normal accounts: {normal_accounts}"
    )

    ring_count = sum(
        1
        for identity in identities
        if identity.get(
            "ring_id"
        )
    )

    print(
        f"\nAccounts with ring information: {ring_count}"
    )

    return df


# ============================================================
# SIMILARITY DISTRIBUTION
# ============================================================

def calculate_similarity_distribution(
    identities: List[Dict[str, Any]]
):

    print("\n" + "=" * 60)
    print("CREATING BEHAVIOURAL VECTORS")
    print("=" * 60)

    vectors = [
        vectorize_identity(
            identity
        )
        for identity in identities
    ]

    matrix = np.asarray(
        vectors,
        dtype=np.float64
    )

    print(
        f"Vector matrix shape: {matrix.shape}"
    )

    print(
        f"Vector dimension: {matrix.shape[1]}"
    )

    # --------------------------------------------------------
    # Standardise features across accounts
    # --------------------------------------------------------

    mean = np.mean(
        matrix,
        axis=0
    )

    std = np.std(
        matrix,
        axis=0
    )

    std[
        std < 1e-8
    ] = 1.0

    matrix = (
        matrix - mean
    ) / std

    matrix = np.nan_to_num(
        matrix,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    # --------------------------------------------------------
    # Normalise rows ONLY after feature standardisation.
    # --------------------------------------------------------

    norms = np.linalg.norm(
        matrix,
        axis=1,
        keepdims=True
    )

    norms[
        norms < 1e-8
    ] = 1.0

    matrix = (
        matrix / norms
    )

    # --------------------------------------------------------
    # Similarity matrix
    # --------------------------------------------------------

    similarity_matrix = (
        matrix @ matrix.T
    )

    n = len(
        identities
    )

    similarities = []

    for i in range(n):

        for j in range(
            i + 1,
            n
        ):

            similarities.append(
                float(
                    similarity_matrix[i, j]
                )
            )

    similarities = np.asarray(
        similarities,
        dtype=np.float64
    )

    print("\n" + "=" * 60)
    print("SIMILARITY DISTRIBUTION")
    print("=" * 60)

    print(
        f"Pairwise comparisons: {len(similarities)}"
    )

    if len(similarities) > 0:

        print(
            f"Minimum similarity: {np.min(similarities):.4f}"
        )

        print(
            f"Maximum similarity: {np.max(similarities):.4f}"
        )

        print(
            f"Mean similarity: {np.mean(similarities):.4f}"
        )

        print(
            f"Median similarity: {np.median(similarities):.4f}"
        )

        print(
            f"90th percentile: {np.percentile(similarities, 90):.4f}"
        )

        print(
            f"95th percentile: {np.percentile(similarities, 95):.4f}"
        )

        print(
            f"99th percentile: {np.percentile(similarities, 99):.4f}"
        )

    return similarities


# ============================================================
# GRAPH STATISTICS
# ============================================================

def calculate_graph_statistics(
    graph: Dict[str, Any]
) -> Dict[str, Any]:

    nodes = graph.get(
        "nodes",
        []
    )

    edges = graph.get(
        "edges",
        []
    )

    G = nx.Graph()

    for node in nodes:

        G.add_node(
            node["id"]
        )

    for edge in edges:

        G.add_edge(
            edge["source"],
            edge["target"],
            weight=edge.get(
                "weight",
                0.0
            )
        )

    components = list(
        nx.connected_components(
            G
        )
    )

    multi_account_clusters = [
        c
        for c in components
        if len(c) >= 2
    ]

    largest_cluster = (
        max(
            [
                len(c)
                for c in components
            ]
        )
        if components
        else 0
    )

    average_degree = (
        float(
            np.mean(
                [
                    degree
                    for _, degree
                    in G.degree()
                ]
            )
        )
        if len(G) > 0
        else 0.0
    )

    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "connected_components": len(
            components
        ),
        "multi_account_clusters": len(
            multi_account_clusters
        ),
        "largest_cluster": largest_cluster,
        "average_degree": average_degree,
    }


# ============================================================
# THRESHOLD ANALYSIS
# ============================================================

def run_threshold_analysis(
    identities: List[Dict[str, Any]]
):

    print("\n" + "=" * 60)
    print("SIMILARITY THRESHOLD ANALYSIS")
    print("=" * 60)

    results = []

    for threshold in THRESHOLDS:

        graph = build_similarity_graph(
            identities,
            similarity_threshold=threshold
        )

        stats = calculate_graph_statistics(
            graph
        )

        results.append(
            {
                "threshold": threshold,
                **stats,
            }
        )

        print(
            f"\nThreshold: {threshold:.2f}"
        )

        print(
            f"Nodes:     {stats['nodes']}"
        )

        print(
            f"Edges:     {stats['edges']}"
        )

        print(
            f"Connected components: "
            f"{stats['connected_components']}"
        )

        print(
            f"Multi-account clusters: "
            f"{stats['multi_account_clusters']}"
        )

        print(
            f"Largest cluster: "
            f"{stats['largest_cluster']}"
        )

        print(
            f"Average degree: "
            f"{stats['average_degree']:.2f}"
        )

    return results


# ============================================================
# THRESHOLD SELECTION
# ============================================================

def select_threshold(
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:

    """
    Select a threshold that avoids:

        - zero edges
        - one giant fully-connected cluster

    Preference is given to thresholds producing multiple
    meaningful clusters.
    """

    if not results:

        raise ValueError(
            "No threshold results available."
        )

    # --------------------------------------------------------
    # Prefer thresholds where:
    #
    #   edges > 0
    #   clusters > 1
    #   largest cluster < total nodes
    #
    # --------------------------------------------------------

    candidates = []

    for result in results:

        if (
            result["edges"] > 0
            and result["multi_account_clusters"] > 1
            and result["largest_cluster"]
            < result["nodes"]
        ):

            candidates.append(
                result
            )

    if candidates:

        # Choose the highest threshold among meaningful
        # graph structures. Higher threshold generally means
        # stronger similarity.
        selected = max(
            candidates,
            key=lambda x: x["threshold"]
        )

    else:

        # Fall back to the threshold with the least dense
        # non-empty graph.
        non_empty = [
            r
            for r in results
            if r["edges"] > 0
        ]

        if non_empty:

            selected = min(
                non_empty,
                key=lambda x: x["edges"]
            )

        else:

            selected = results[0]

    return selected


# ============================================================
# CLUSTER DISPLAY
# ============================================================

def display_clusters(
    graph: Dict[str, Any],
    top_n: int = 10
):

    print("\n" + "=" * 60)
    print("LARGEST SIMILARITY CLUSTERS")
    print("=" * 60)

    G = nx.Graph()

    for node in graph.get(
        "nodes",
        []
    ):

        G.add_node(
            node["id"]
        )

    for edge in graph.get(
        "edges",
        []
    ):

        G.add_edge(
            edge["source"],
            edge["target"],
            weight=edge.get(
                "weight",
                0.0
            )
        )

    components = sorted(
        nx.connected_components(
            G
        ),
        key=len,
        reverse=True
    )

    displayed = 0

    for index, component in enumerate(
        components,
        start=1
    ):

        if len(component) < 2:
            continue

        print(
            f"\nCluster {index}"
        )

        print(
            f"Size: {len(component)}"
        )

        members = list(
            component
        )

        print(
            "Members:"
        )

        print(
            members[:20]
        )

        if len(members) > 20:

            print(
                f"... and "
                f"{len(members) - 20} more"
            )

        displayed += 1

        if displayed >= top_n:
            break

    if displayed == 0:

        print(
            "\nNo multi-account clusters found."
        )


# ============================================================
# SAVE GRAPH
# ============================================================

def save_graph(
    graph: Dict[str, Any]
):

    print("\n" + "=" * 60)
    print("SAVING GRAPH")
    print("=" * 60)

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            graph,
            f,
            indent=2
        )

    print(
        f"\nGraph saved to:\n{OUTPUT_PATH}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("VERITRACE - LAYER 5")
    print("CROSS-ACCOUNT SIMILARITY GRAPH")
    print("=" * 60)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    identities = load_forge()

    if not identities:

        raise ValueError(
            "No Forge identities found."
        )

    # --------------------------------------------------------
    # Ground truth information
    # --------------------------------------------------------

    ground_truth = build_ground_truth(
        identities
    )

    fraud_count = int(
        ground_truth[
            "actual_attack"
        ].sum()
    )

    normal_count = int(
        len(ground_truth)
        - fraud_count
    )

    # --------------------------------------------------------
    # Explain evaluation limitation
    # --------------------------------------------------------

    if normal_count == 0:

        print(
            "\nWARNING:"
        )

        print(
            "Forge identity dataset contains ONLY attack accounts."
        )

        print(
            "Precision/Recall/F1 against normal accounts "
            "cannot be meaningfully calculated."
        )

        print(
            "Layer 5 will therefore be evaluated using "
            "graph/cluster statistics."
        )

    # --------------------------------------------------------
    # Similarity distribution
    # --------------------------------------------------------

    calculate_similarity_distribution(
        identities
    )

    # --------------------------------------------------------
    # Threshold analysis
    # --------------------------------------------------------

    threshold_results = run_threshold_analysis(
        identities
    )

    # --------------------------------------------------------
    # Select threshold
    # --------------------------------------------------------

    selected = select_threshold(
        threshold_results
    )

    selected_threshold = selected[
        "threshold"
    ]

    print("\n" + "=" * 60)
    print("SELECTED THRESHOLD")
    print("=" * 60)

    print(
        f"Selected threshold: "
        f"{selected_threshold:.2f}"
    )

    print(
        f"Edges: "
        f"{selected['edges']}"
    )

    print(
        f"Multi-account clusters: "
        f"{selected['multi_account_clusters']}"
    )

    print(
        f"Largest cluster: "
        f"{selected['largest_cluster']}"
    )

    print(
        f"Average degree: "
        f"{selected['average_degree']:.2f}"
    )

    # --------------------------------------------------------
    # Build final graph
    # --------------------------------------------------------

    graph = build_similarity_graph(
        identities,
        similarity_threshold=selected_threshold
    )

    # --------------------------------------------------------
    # Display clusters
    # --------------------------------------------------------

    display_clusters(
        graph
    )

    # --------------------------------------------------------
    # Fraud ring information
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("FRAUD RING GRAPH STATISTICS")
    print("=" * 60)

    print(
        f"Total accounts: "
        f"{graph['total_nodes']}"
    )

    print(
        f"Similarity edges: "
        f"{graph['total_edges']}"
    )

    G = nx.Graph()

    for node in graph[
        "nodes"
    ]:

        G.add_node(
            node["id"]
        )

    for edge in graph[
        "edges"
    ]:

        G.add_edge(
            edge["source"],
            edge["target"]
        )

    components = list(
        nx.connected_components(
            G
        )
    )

    multi_clusters = [
        c
        for c in components
        if len(c) >= 2
    ]

    print(
        f"Connected components: "
        f"{len(components)}"
    )

    print(
        f"Multi-account clusters: "
        f"{len(multi_clusters)}"
    )

    if multi_clusters:

        print(
            "\nLargest clusters:"
        )

        for i, cluster in enumerate(
            sorted(
                multi_clusters,
                key=len,
                reverse=True
            )[:10],
            start=1
        ):

            print(
                f"Cluster {i}: "
                f"{len(cluster)} accounts"
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_graph(
        graph
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LAYER 5 COMPLETE")
    print("=" * 60)

    print(
        f"\nLayer 5 successfully generated "
        f"a cross-account behavioural similarity graph."
    )

    print(
        f"Accounts: "
        f"{graph['total_nodes']}"
    )

    print(
        f"Similarity edges: "
        f"{graph['total_edges']}"
    )

    print(
        f"Clusters: "
        f"{len(multi_clusters)}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()