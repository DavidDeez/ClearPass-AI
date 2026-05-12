"""
Module 2 — Financial Feature Extractor (Layer 2)
==================================================
Transforms raw Open Banking transaction lists into a fixed-width
feature vector consumed by all three downstream AI models.

Each feature is designed to capture a different dimension of financial
health — income stability, spending discipline, loan exposure, and
account activity depth.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger("clearpass.feature_extractor")

# Keywords indicating loan-related activity in narration text
_LOAN_KEYWORDS = re.compile(
    r"\b(loan|lend|borrow|credit|repay)\b",
    re.IGNORECASE,
)


def extract_features(transactions: list[dict[str, Any]]) -> dict[str, float]:
    """
    Derive behavioural features from a list of bank transactions.

    Parameters
    ----------
    transactions : list[dict]
        Each element must contain:
        - amount   (float): transaction amount in NGN
        - date     (str):   ISO-8601 date string (e.g. "2025-03-15")
        - status   (str):   "successful" | "failed" | etc.
        - narration(str):   free-text description
        - type     (str):   "credit" | "debit"

    Returns
    -------
    dict[str, float]
        Feature vector with keys:
        avg_monthly_income, income_std, failed_tx_rate,
        loan_keyword_count, avg_monthly_spend, credit_debit_ratio,
        active_months
    """
    logger.info("Extracting features from %d transactions", len(transactions))

    if not transactions:
        logger.warning("Empty transaction list — returning zero-vector")
        return {
            "avg_monthly_income": 0.0,
            "income_std": 0.0,
            "failed_tx_rate": 0.0,
            "loan_keyword_count": 0.0,
            "avg_monthly_spend": 0.0,
            "credit_debit_ratio": 0.0,
            "active_months": 0.0,
        }

    # Buckets: year-month -> list of amounts
    monthly_credits: dict[str, list[float]] = defaultdict(list)
    monthly_debits: dict[str, list[float]] = defaultdict(list)

    total_credits = 0.0
    total_debits = 0.0
    failed_count = 0
    loan_keyword_count = 0
    active_month_set: set[str] = set()

    for tx in transactions:
        amount = float(tx.get("amount", 0))
        date_str = tx.get("date", "")
        status = str(tx.get("status", "")).strip().lower()
        narration = str(tx.get("narration", ""))
        tx_type = str(tx.get("type", "")).strip().lower()

        # Parse month key
        try:
            dt = datetime.fromisoformat(date_str)
            month_key = dt.strftime("%Y-%m")
        except (ValueError, TypeError):
            logger.debug("Unparsable date '%s' — skipping month bucket", date_str)
            month_key = None

        if month_key:
            active_month_set.add(month_key)

        # Accumulate credits / debits
        if tx_type == "credit":
            total_credits += amount
            if month_key:
                monthly_credits[month_key].append(amount)
        elif tx_type == "debit":
            total_debits += amount
            if month_key:
                monthly_debits[month_key].append(amount)

        # Failed transactions
        if status == "failed":
            failed_count += 1

        # Loan keyword scan
        loan_keyword_count += len(_LOAN_KEYWORDS.findall(narration))

    # --- Derived features ---
    n_transactions = len(transactions)

    # Monthly credit totals -> mean & std
    credit_month_totals = [
        sum(amounts) for amounts in monthly_credits.values()
    ]
    avg_monthly_income = float(np.mean(credit_month_totals)) if credit_month_totals else 0.0
    income_std = float(np.std(credit_month_totals, ddof=1)) if len(credit_month_totals) > 1 else 0.0

    # Monthly debit totals -> mean
    debit_month_totals = [
        sum(amounts) for amounts in monthly_debits.values()
    ]
    avg_monthly_spend = float(np.mean(debit_month_totals)) if debit_month_totals else 0.0

    # Ratios
    failed_tx_rate = failed_count / n_transactions if n_transactions > 0 else 0.0
    credit_debit_ratio = (total_credits / total_debits) if total_debits > 0 else 0.0

    active_months = float(len(active_month_set))

    features = {
        "avg_monthly_income": round(avg_monthly_income, 2),
        "income_std": round(income_std, 2),
        "failed_tx_rate": round(failed_tx_rate, 4),
        "loan_keyword_count": float(loan_keyword_count),
        "avg_monthly_spend": round(avg_monthly_spend, 2),
        "credit_debit_ratio": round(credit_debit_ratio, 4),
        "active_months": active_months,
    }

    logger.info("Feature extraction complete: %s", features)
    return features
