"""
Module 4 — Model B: Isolation Forest Ghost Borrower Detector (Layer 3)
=======================================================================
Unsupervised anomaly detector trained on normal borrower profiles.
Flags synthetic/fraudulent identities as ghost borrowers.
Decision_function output normalised to 0–100 (higher = safer).
"""

import logging
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from services.synthetic_data import generate_synthetic_data

logger = logging.getLogger("clearpass.model_b")

ANOMALY_FEATURES = [
    "loan_keyword_count",
    "credit_debit_ratio",
    "failed_tx_rate",
    "avg_monthly_income",
]


def _train_model() -> tuple[IsolationForest, StandardScaler, float, float]:
    logger.info("Training Model B (Isolation Forest)…")
    df = generate_synthetic_data(n_samples=150, seed=99, for_anomaly=True)
    X = df[ANOMALY_FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1,
    )
    model.fit(X_scaled)

    train_scores = model.decision_function(X_scaled)
    score_min = float(train_scores.min())
    score_max = float(train_scores.max())
    logger.info("Model B trained — range: [%.4f, %.4f]", score_min, score_max)
    return model, scaler, score_min, score_max


_model, _scaler, _score_min, _score_max = _train_model()


def _normalize_score(raw: float) -> float:
    if _score_max == _score_min:
        return 50.0
    normalized = (raw - _score_min) / (_score_max - _score_min) * 100
    return float(np.clip(normalized, 0, 100))


def detect_anomaly(features: dict[str, float]) -> dict[str, Any]:
    """
    Score how normal a borrower profile looks.

    Returns dict with anomaly_score (0–100), is_ghost_borrower, raw_score.
    """
    logger.info("Running anomaly detection")
    x = np.array([[features.get(f, 0.0) for f in ANOMALY_FEATURES]])
    x_scaled = _scaler.transform(x)

    raw_score = float(_model.decision_function(x_scaled)[0])
    prediction = int(_model.predict(x_scaled)[0])
    anomaly_score = round(_normalize_score(raw_score), 2)
    is_ghost = prediction == -1

    logger.info("Model B — score: %.2f, ghost: %s", anomaly_score, is_ghost)
    return {
        "anomaly_score": anomaly_score,
        "is_ghost_borrower": is_ghost,
        "raw_score": round(raw_score, 4),
    }
