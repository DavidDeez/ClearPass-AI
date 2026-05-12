"""
Synthetic Data Generator for ClearPass AI Models
=================================================
Generates realistic synthetic borrower data modelled on Nigerian fintech
distributions. Used by Model A (XGBoost Behavior Profiler) and Model B
(Isolation Forest Ghost Borrower Detector) for training at startup.

Income distributions are in NGN (Nigerian Naira), with realistic ranges
and failure rates observed in the Nigerian digital lending ecosystem.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("clearpass.synthetic_data")


def generate_synthetic_data(
    n_samples: int = 200,
    seed: int = 42,
    for_anomaly: bool = False,
) -> pd.DataFrame:
    """
    Generate a DataFrame of synthetic borrower profiles.

    Parameters
    ----------
    n_samples : int
        Number of synthetic borrower records to create.
    seed : int
        Random seed for reproducibility.
    for_anomaly : bool
        If True, generate only *normal* borrower profiles (no bad-borrower
        skew) — used by Model B's IsolationForest which is fitted on
        normal data only.

    Returns
    -------
    pd.DataFrame
        Columns:
        - avg_monthly_income   (NGN, 30 000 – 500 000)
        - income_std           (NGN, variability of income)
        - failed_tx_rate       (0.00 – 0.25)
        - loan_keyword_count   (0 – 30)
        - avg_monthly_spend    (NGN)
        - credit_debit_ratio   (0.5 – 3.0+)
        - active_months        (1 – 24)
        - repaid_on_time       (0 or 1, only when for_anomaly=False)
    """
    rng = np.random.default_rng(seed)
    logger.info(
        "Generating %d synthetic samples (anomaly_mode=%s)", n_samples, for_anomaly
    )

    # --- Income: log-normal distribution centered around ₦120k/month ---
    avg_monthly_income = np.clip(
        rng.lognormal(mean=np.log(120_000), sigma=0.6, size=n_samples),
        30_000,
        500_000,
    )

    # --- Income volatility: proportional to income level ---
    income_std = avg_monthly_income * rng.uniform(0.05, 0.45, size=n_samples)

    # --- Failed transaction rate: beta distribution skewed low ---
    failed_tx_rate = np.clip(
        rng.beta(a=1.5, b=20, size=n_samples),
        0.0,
        0.25,
    )

    # --- Loan keyword count: Poisson-like (most people have few mentions) ---
    loan_keyword_count = rng.poisson(lam=4, size=n_samples).astype(float)

    # --- Monthly spend: 40–90 % of income ---
    spend_ratio = rng.uniform(0.40, 0.90, size=n_samples)
    avg_monthly_spend = avg_monthly_income * spend_ratio

    # --- Credit / Debit ratio: spend_ratio inverse + noise ---
    credit_debit_ratio = np.clip(
        (1.0 / spend_ratio) + rng.normal(0, 0.15, size=n_samples),
        0.5,
        4.0,
    )

    # --- Active months: uniform 3–24 for normal, 1–6 for risky ---
    if for_anomaly:
        active_months = rng.integers(6, 25, size=n_samples).astype(float)
    else:
        active_months = rng.integers(1, 25, size=n_samples).astype(float)

    data = pd.DataFrame(
        {
            "avg_monthly_income": np.round(avg_monthly_income, 2),
            "income_std": np.round(income_std, 2),
            "failed_tx_rate": np.round(failed_tx_rate, 4),
            "loan_keyword_count": loan_keyword_count,
            "avg_monthly_spend": np.round(avg_monthly_spend, 2),
            "credit_debit_ratio": np.round(credit_debit_ratio, 4),
            "active_months": active_months,
        }
    )

    if not for_anomaly:
        # --- Target variable: repaid_on_time ---
        # Good-borrower probability rises with income, low failed-rate,
        # high credit/debit ratio, and more active months.
        logit = (
            0.6
            + 0.000005 * avg_monthly_income
            - 3.0 * failed_tx_rate
            + 0.3 * credit_debit_ratio
            + 0.04 * active_months
            - 0.02 * loan_keyword_count
            + rng.normal(0, 0.3, size=n_samples)
        )
        prob = 1 / (1 + np.exp(-logit))
        repaid_on_time = (rng.random(size=n_samples) < prob).astype(int)
        data["repaid_on_time"] = repaid_on_time

    logger.info(
        "Synthetic data generated — shape: %s, columns: %s",
        data.shape,
        list(data.columns),
    )
    return data
