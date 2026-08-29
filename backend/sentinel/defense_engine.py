import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# VERITRACE - LAYER 4
# REAL-TIME DEFENSE / DECISION ENGINE
# ============================================================

RESULTS_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "results"
)

INPUT_FILE = RESULTS_DIR / "forge_risk_fusion_predictions.csv"
OUTPUT_FILE = RESULTS_DIR / "forge_defense_results.csv"


# ------------------------------------------------------------
# Initial risk thresholds
# ------------------------------------------------------------

NORMAL_THRESHOLD = 0.30
HIGH_RISK_THRESHOLD = 0.60


def classify_risk(score):
    """
    Convert final risk score into a defense decision.
    """

    if score < NORMAL_THRESHOLD:
        return "NORMAL"

    elif score < HIGH_RISK_THRESHOLD:
        return "REVIEW"

    else:
        return "BLOCK"


def generate_reason(row):
    """
    Generate an interpretable reason for the decision.
    """

    xgb = row["xgb_fraud_score"]
    anomaly = row["anomaly_score"]
    risk = row["final_risk_score"]

    reasons = []

    if xgb >= 0.60:
        reasons.append(
            "High ML fraud probability"
        )
    elif xgb >= 0.30:
        reasons.append(
            "Elevated ML fraud probability"
        )

    if anomaly > 0:
        reasons.append(
            "Behavioral anomaly detected"
        )

    if risk >= HIGH_RISK_THRESHOLD:
        reasons.append(
            "Overall risk exceeds blocking threshold"
        )

    if not reasons:
        reasons.append(
            "Transaction behavior appears normal"
        )

    return "; ".join(reasons)


def apply_defense(df):

    data = df.copy()

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_columns = [
        "account_id",
        "final_risk_score",
        "xgb_fraud_score",
        "anomaly_score",
    ]

    missing = [
        col
        for col in required_columns
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # --------------------------------------------------------
    # Ensure numeric risk values
    # --------------------------------------------------------

    for column in [
        "final_risk_score",
        "xgb_fraud_score",
        "anomaly_score",
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        ).fillna(0.0)

    # --------------------------------------------------------
    # Risk decision
    # --------------------------------------------------------

    data["defense_action"] = (
        data["final_risk_score"]
        .apply(classify_risk)
    )

    # --------------------------------------------------------
    # Explainability
    # --------------------------------------------------------

    data["risk_reason"] = data.apply(
        generate_reason,
        axis=1
    )

    # --------------------------------------------------------
    # Recommended response
    # --------------------------------------------------------

    action_map = {
        "NORMAL": "ALLOW",
        "REVIEW": "STEP_UP_AUTHENTICATION",
        "BLOCK": "BLOCK_TRANSACTION",
    }

    data["recommended_action"] = (
        data["defense_action"]
        .map(action_map)
    )

    return data


def print_summary(df):

    print()
    print("=" * 60)
    print("DEFENSE DECISION SUMMARY")
    print("=" * 60)

    print("\nDefense decisions:")

    print(
        df["defense_action"]
        .value_counts()
    )

    print("\nRecommended actions:")

    print(
        df["recommended_action"]
        .value_counts()
    )

    print("\nRisk statistics:")

    print(
        df["final_risk_score"].describe()
    )

    print("\nSample decisions:")

    columns = [
        "account_id",
        "xgb_fraud_score",
        "anomaly_score",
        "final_risk_score",
        "defense_action",
        "recommended_action",
        "risk_reason",
    ]

    print(
        df[columns]
        .head(20)
        .to_string(index=False)
    )


def main():

    print("=" * 60)
    print("VERITRACE - LAYER 4")
    print("REAL-TIME DEFENSE / DECISION ENGINE")
    print("=" * 60)

    # --------------------------------------------------------
    # Load Layer 3 output
    # --------------------------------------------------------

    print("\nLoading Layer 3 results...")

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Layer 3 output not found:\n{INPUT_FILE}\n\n"
            "Run risk_fusion.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded {len(df)} transactions."
    )

    # --------------------------------------------------------
    # Apply defense
    # --------------------------------------------------------

    print("\nApplying defense decisions...")

    result = apply_defense(df)

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print_summary(result)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 60)
    print("LAYER 4 COMPLETE")
    print("=" * 60)

    print(
        f"\nResults saved to:\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()