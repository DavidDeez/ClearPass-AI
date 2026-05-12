"""
Module 5 — Model C: Identity Fraud Graph (Layer 3)
====================================================
Maintains an in-memory NetworkX graph of identity relationships.
Nodes = BVNs. Edges connect BVNs sharing a phone, device, or address.
Louvain community detection identifies fraud rings (clusters > 3 BVNs).
Graph score: 0–100 (higher = safer / smaller cluster).
"""

import json
import logging
import os
from typing import Any

import community as community_louvain
import networkx as nx

logger = logging.getLogger("clearpass.model_c")

GRAPH_PERSISTENCE_PATH = os.environ.get(
    "CLEARPASS_GRAPH_PATH", "identity_graph.json"
)


def _load_graph() -> nx.Graph:
    """Load graph from JSON file or return an empty graph."""
    if os.path.exists(GRAPH_PERSISTENCE_PATH):
        try:
            with open(GRAPH_PERSISTENCE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            G = nx.node_link_graph(data)
            logger.info("Loaded identity graph — %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
            return G
        except Exception as exc:
            logger.warning("Could not load graph from %s: %s", GRAPH_PERSISTENCE_PATH, exc)
    return nx.Graph()


def _save_graph(G: nx.Graph) -> None:
    """Persist graph to JSON."""
    try:
        data = nx.node_link_data(G)
        with open(GRAPH_PERSISTENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.debug("Graph saved — %d nodes", G.number_of_nodes())
    except Exception as exc:
        logger.error("Failed to save graph: %s", exc)


_graph = _load_graph()


def add_user_to_graph(bvn: str, phone: str, device_id: str, address: str) -> None:
    """
    Insert a BVN into the identity graph and draw edges to any
    existing BVN that shares a phone, device_id, or address.
    """
    logger.info("Adding BVN %s to identity graph", bvn[:6] + "****")

    if not _graph.has_node(bvn):
        _graph.add_node(bvn, phone=phone, device_id=device_id, address=address)

    # Check every existing node for shared attributes
    for existing_bvn, attrs in list(_graph.nodes(data=True)):
        if existing_bvn == bvn:
            continue
        shared = []
        if attrs.get("phone") == phone:
            shared.append("phone")
        if attrs.get("device_id") == device_id:
            shared.append("device_id")
        if attrs.get("address") == address:
            shared.append("address")

        if shared:
            if _graph.has_edge(bvn, existing_bvn):
                _graph[bvn][existing_bvn]["shared"] = shared
            else:
                _graph.add_edge(bvn, existing_bvn, shared=shared)
            logger.info("Edge %s <-> %s via %s", bvn[:6], existing_bvn[:6], shared)

    _save_graph(_graph)


def score_graph(bvn: str) -> dict[str, Any]:
    """
    Run Louvain community detection and score the BVN's cluster.

    Returns dict with cluster_size, is_fraud_ring, graph_score, shared_attributes.
    """
    logger.info("Scoring graph for BVN %s", bvn[:6] + "****")

    if not _graph.has_node(bvn):
        logger.info("BVN not in graph — returning safe defaults")
        return {
            "cluster_size": 1,
            "is_fraud_ring": False,
            "graph_score": 100.0,
            "shared_attributes": [],
        }

    # Louvain requires at least one edge; handle isolated nodes
    if _graph.number_of_edges() == 0:
        return {
            "cluster_size": 1,
            "is_fraud_ring": False,
            "graph_score": 100.0,
            "shared_attributes": [],
        }

    partition = community_louvain.best_partition(_graph)
    user_community = partition.get(bvn)
    cluster_members = [n for n, c in partition.items() if c == user_community]
    cluster_size = len(cluster_members)

    # Collect shared attributes from edges to neighbours
    shared_attrs: set[str] = set()
    for neighbour in _graph.neighbors(bvn):
        edge_data = _graph[bvn][neighbour]
        for attr in edge_data.get("shared", []):
            shared_attrs.add(attr)

    is_fraud_ring = cluster_size > 3
    # Score: 100 for isolated, drops with cluster size
    graph_score = max(0.0, 100.0 - (cluster_size - 1) * 20.0)

    logger.info(
        "Model C — cluster: %d, fraud_ring: %s, score: %.1f",
        cluster_size, is_fraud_ring, graph_score,
    )

    return {
        "cluster_size": cluster_size,
        "is_fraud_ring": is_fraud_ring,
        "graph_score": round(graph_score, 2),
        "shared_attributes": sorted(shared_attrs),
    }
