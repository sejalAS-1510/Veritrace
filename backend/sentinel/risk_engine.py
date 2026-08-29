"""
VeriTrace Sentinel - Risk Engine

Converts XGBoost risk probabilities into:

    LOW
    MEDIUM
    HIGH
    CRITICAL

and recommends an action.
"""


import pandas as pd
import numpy as np


# ============================================================
# THRESHOLDS
# ============================================================

LOW_THRESHOLD = 0.10

MEDIUM_THRESHOLD = 0.30

HIGH_THRESHOLD = 0.50

CRITICAL_THRESHOLD = 0.80


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(score):

    score = float(score)

    if score < LOW_THRESHOLD:
        return "LOW"

    elif score < MEDIUM_THRESHOLD:
        return "MEDIUM"

    elif score < HIGH_THRESHOLD:
        return "HIGH"

    elif score < CRITICAL_THRESHOLD:
        return "CRITICAL"

    else:
        return "CRITICAL"


# ============================================================
# ACTION
# ============================================================

def get_action(category):

    actions = {

        "LOW":
            "ALLOW",

        "MEDIUM":
            "MONITOR",

        "HIGH":
            "STEP_UP_VERIFICATION",

        "CRITICAL":
            "BLOCK_OR_MANUAL_REVIEW"
    }

    return actions.get(
        category,
        "MANUAL_REVIEW"
    )


# ============================================================
# PROCESS TRANSACTION RISK
# ============================================================

def process_transaction_risk(
    predictions
):

    if "risk_score" not in predictions.columns:

        raise ValueError(
            "Missing required column: risk_score"
        )

    result = predictions.copy()

    # Ensure numeric

    result[
        "risk_score"
    ] = pd.to_numeric(
        result[
            "risk_score"
        ],
        errors="coerce"
    ).fillna(0.0)

    # Valid probability

    result[
        "risk_score"
    ] = result[
        "risk_score"
    ].clip(
        0.0,
        1.0
    )

    # Category

    result[
        "risk_category"
    ] = result[
        "risk_score"
    ].apply(
        classify_risk
    )

    # Action

    result[
        "recommended_action"
    ] = result[
        "risk_category"
    ].apply(
        get_action
    )

    return result


# ============================================================
# ACCOUNT-LEVEL RISK
# ============================================================

def calculate_account_risk(
    predictions
):

    required_columns = [
        "account_id",
        "risk_score"
    ]

    for column in required_columns:

        if column not in predictions.columns:

            raise ValueError(
                f"Missing required column: {column}"
            )

    df = predictions.copy()

    df[
        "risk_score"
    ] = pd.to_numeric(
        df[
            "risk_score"
        ],
        errors="coerce"
    ).fillna(0.0)

    # --------------------------------------------------------
    # If prediction column isn't present,
    # derive it using 0.50.
    # --------------------------------------------------------

    if "prediction" not in df.columns:

        df[
            "prediction"
        ] = (
            df[
                "risk_score"
            ] >= 0.50
        ).astype(int)

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    account_risk = (
        df
        .groupby(
            "account_id"
        )
        .agg(

            max_risk_score=(
                "risk_score",
                "max"
            ),

            avg_risk_score=(
                "risk_score",
                "mean"
            ),

            transaction_count=(
                "risk_score",
                "count"
            ),

            flagged_transactions=(
                "prediction",
                "sum"
            )
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Flag ratio
    # --------------------------------------------------------

    account_risk[
        "flag_ratio"
    ] = (
        account_risk[
            "flagged_transactions"
        ]
        /
        account_risk[
            "transaction_count"
        ].clip(
            lower=1
        )
    )

    # --------------------------------------------------------
    # Account score
    # --------------------------------------------------------
    #
    # Maximum risk:
    #     60%
    #
    # Average risk:
    #     25%
    #
    # Flag ratio:
    #     15%
    #

    account_risk[
        "account_risk_score"
    ] = (

        0.60
        * account_risk[
            "max_risk_score"
        ]

        +

        0.25
        * account_risk[
            "avg_risk_score"
        ]

        +

        0.15
        * account_risk[
            "flag_ratio"
        ]
    )

    account_risk[
        "account_risk_score"
    ] = account_risk[
        "account_risk_score"
    ].clip(
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Account category
    # --------------------------------------------------------

    account_risk[
        "risk_category"
    ] = account_risk[
        "account_risk_score"
    ].apply(
        classify_risk
    )

    # --------------------------------------------------------
    # Account action
    # --------------------------------------------------------

    account_risk[
        "recommended_action"
    ] = account_risk[
        "risk_category"
    ].apply(
        get_action
    )

    return account_risk


# ============================================================
# COMPLETE RISK PIPELINE
# ============================================================

def run_risk_engine(
    transaction_predictions
):

    transaction_results = (
        process_transaction_risk(
            transaction_predictions
        )
    )

    account_results = (
        calculate_account_risk(
            transaction_results
        )
    )

    return (
        transaction_results,
        account_results
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("VERITRACE RISK ENGINE")
    print("=" * 60)

    test_data = pd.DataFrame({

        "account_id": [
            "SYN-001",
            "SYN-001",
            "SYN-001",
            "SYN-002",
            "SYN-002",
            "SYN-003"
        ],

        "risk_score": [
            0.02,
            0.05,
            0.87,
            0.12,
            0.25,
            0.95
        ],

        "prediction": [
            0,
            0,
            1,
            0,
            0,
            1
        ]
    })

    transaction_results, account_results = (
        run_risk_engine(
            test_data
        )
    )

    print()
    print("TRANSACTION RISK")
    print()

    print(
        transaction_results.to_string(
            index=False
        )
    )

    print()
    print("ACCOUNT RISK")
    print()

    print(
        account_results.to_string(
            index=False
        )
    )

    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)