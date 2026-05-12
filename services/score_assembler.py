"""
Module 6 — Trust Score Assembler (Layer 4)
============================================
Combines the three model outputs into a single weighted trust score
(0–100) and issues a verdict: PASS, REVIEW, or BLOCK.

Weights:
  Model A (Behavior Profiler)    = 50 %
  Model B (Ghost Borrower Det.)  = 30 %
  Model C (Identity Fraud Graph) = 20 %
"""

import logging
from typing import Any

logger = logging.getLogger("clearpass.score_assembler")

WEIGHT_A = 0.50
WEIGHT_B = 0.30
WEIGHT_C = 0.20


def assemble_trust_score(
    model_a: dict[str, Any],
    model_b: dict[str, Any],
    model_c: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce the final ClearPass trust score and verdict.

    Parameters
    ----------
    model_a : dict  — output of score_behavior()
    model_b : dict  — output of detect_anomaly()
    model_c : dict  — output of score_graph()

    Returns
    -------
    dict with trust_score, verdict, and nested explanation.
    """
    score_a = float(model_a.get("score", 0))
    score_b = float(model_b.get("anomaly_score", 0))
    score_c = float(model_c.get("graph_score", 0))

    raw = WEIGHT_A * score_a + WEIGHT_B * score_b + WEIGHT_C * score_c
    trust_score = int(round(raw))

    if trust_score >= 60:
        verdict = "PASS"
    elif trust_score >= 40:
        verdict = "REVIEW"
    else:
        verdict = "BLOCK"

    result = {
        "trust_score": trust_score,
        "verdict": verdict,
        "explanation": {
            "behavior": model_a.get("top_reasons", []),
            "anomaly": {
                "is_ghost_borrower": model_b.get("is_ghost_borrower", False),
                "anomaly_score": score_b,
            },
            "graph": {
                "cluster_size": model_c.get("cluster_size", 1),
                "is_fraud_ring": model_c.get("is_fraud_ring", False),
            },
        },
    }

    logger.info(
        "Trust score assembled — score: %d, verdict: %s (A=%.1f B=%.1f C=%.1f)",
        trust_score, verdict, score_a, score_b, score_c,
    )
    return result
