"""
Module 3 — Model A: XGBoost Behavior Profiler (Layer 3)
========================================================
Supervised classifier trained on synthetic Nigerian fintech borrower
data. Predicts the probability that a user will repay on time, then
maps that probability to a 0–100 trust sub-score.

Uses SHAP TreeExplainer for per-prediction, human-readable explanations
of which features drove the score up or down.
"""

import logging
from typing import Any

import numpy as np
import shap
from xgboost import XGBClassifier

from services.synthetic_data import generate_synthetic_data

logger = logging.getLogger("clearpass.model_a")

# ---------------------------------------------------------------------------
# Feature ordering (must be consistent between training and inference)
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "avg_monthly_income",
    "income_std",
    "failed_tx_rate",
    "loan_keyword_count",
    "avg_monthly_spend",
    "credit_debit_ratio",
    "active_months",
]

# Human-readable labels for SHAP explanations
_FEATURE_LABELS = {
    "avg_monthly_income": "Monthly income level",
    "income_std": "Income consistency",
    "failed_tx_rate": "Failed transaction rate",
    "loan_keyword_count": "Loan-related activity",
    "avg_monthly_spend": "Monthly spending level",
    "credit_debit_ratio": "Credit-to-debit ratio",
    "active_months": "Account activity duration",
}


# ---------------------------------------------------------------------------
# Train at module load (startup)
# ---------------------------------------------------------------------------
def _train_model() -> tuple[XGBClassifier, shap.TreeExplainer]:
    """Train the XGBClassifier on synthetic data and attach a SHAP explainer."""
    logger.info("Training Model A (XGBoost Behavior Profiler)…")

    df = generate_synthetic_data(n_samples=200, seed=42, for_anomaly=False)
    X = df[FEATURE_NAMES].values
    y = df["repaid_on_time"].values

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)

    logger.info(
        "Model A trained — classes: %s, n_features: %d",
        model.classes_.tolist(),
        len(FEATURE_NAMES),
    )
    return model, explainer


_model, _explainer = _train_model()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_behavior(features: dict[str, float]) -> dict[str, Any]:
    """
    Score a user's financial behavior and explain the result.

    Parameters
    ----------
    features : dict[str, float]
        Must contain all keys listed in FEATURE_NAMES.

    Returns
    -------
    dict
        {
            "score": float,          # 0–100 trust sub-score
            "top_reasons": list[str] # 3 human-readable SHAP explanations
        }
    """
    logger.info("Scoring behaviour for features: %s", features)

    # Build ordered feature vector
    x = np.array([[features.get(f, 0.0) for f in FEATURE_NAMES]])

    # Probability of class 1 (repaid on time)
    prob = float(_model.predict_proba(x)[0][1])
    score = round(prob * 100, 2)

    # SHAP values for this single prediction
    shap_values = _explainer.shap_values(x)

    # shap_values may be a list (one array per class) or a single array
    if isinstance(shap_values, list):
        sv = shap_values[1][0]   # class-1 SHAP values
    else:
        sv = shap_values[0]

    # Rank features by absolute SHAP impact
    ranked_indices = np.argsort(np.abs(sv))[::-1]

    top_reasons: list[str] = []
    for idx in ranked_indices[:3]:
        feat_name = FEATURE_NAMES[idx]
        label = _FEATURE_LABELS.get(feat_name, feat_name)
        shap_val = sv[idx]
        direction = "increases" if shap_val > 0 else "decreases"
        points = round(abs(shap_val) * 100, 1)
        reason = f"{label} {direction} trust by {points:+.1f} points"
        # Fix the sign in the formatted string for readability
        if direction == "increases":
            reason = f"{label} increases trust by +{points:.1f} points"
        else:
            reason = f"{label} decreases trust by -{points:.1f} points"
        top_reasons.append(reason)

    logger.info("Model A score: %.2f, top reasons: %s", score, top_reasons)

    return {
        "score": score,
        "top_reasons": top_reasons,
    }
