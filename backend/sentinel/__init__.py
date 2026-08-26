"""
VeriTrace Sentinel Module - Adversarial Trajectory Analysis & Similarity Graph
"""
from sentinel.trajectory_model import score_trajectory, extract_features
from sentinel.similarity_graph import build_similarity_graph

__all__ = ["score_trajectory", "extract_features", "build_similarity_graph"]
