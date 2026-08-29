import os
import sys
import joblib
import pandas as pd
import numpy as np

from sklearn.metrics import (
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "..",
    "data"
)

RESULTS_DIR = os.path.join(
    DATA_DIR,
    "results"
)

FORGE_PATH = os.path.join(
    DATA_DIR,
    "generated",
    "batch_attack_timeline.json"
)

XGB_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_unified_fraud_model.pkl"
)

IF_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_anomaly_model.joblib"
)

IF_SCALER_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_scaler.joblib"
)

IF_THRESHOLD_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_threshold.joblib"
)


# ============================================================
# FEATURES
# ============================================================

ML_FEATURES = [
    "transaction_amount",
    "account_age",
    "transaction_count",
    "avg_transaction_amount",
    "std_transaction_amount",
    "max_transaction_amount",
    "avg_time_gap",
    "std_time_gap",
    "cash_out_ratio",
    "payment_ratio",
    "transfer_ratio",
    "debit_ratio",
]


# ============================================================
# LOAD FORGE DATA
# ============================================================

def load_forge_data(path):

    print("=" * 60)
    print("LOADING FORGE DATA")
    print("=" * 60)

    with open(path, "r") as f:
        import json
        raw = json.load(f)

    rows = []

    # --------------------------------------------------------
    # Forge format:
    #
    # account_id
    # profile
    # timeline
    #
    # Each timeline contains transaction objects.
    # --------------------------------------------------------

    if isinstance(raw, list):

        for account in raw:

            account_id = account.get(
                "account_id"
            )

            timeline = account.get(
                "timeline",
                []
            )

            for item in timeline:

                if isinstance(item, dict):

                    transaction = item.get(
                        "transaction",
                        item
                    )

                    if isinstance(transaction, dict):

                        row = transaction.copy()

                        row["account_id"] = (
                            account_id
                        )

                        row["phase"] = (
                            item.get("phase")
                        )

                        row["day"] = (
                            item.get("day")
                        )

                        row["sequence"] = (
                            item.get("sequence")
                        )

                        rows.append(row)

    elif isinstance(raw, dict):

        # Try direct transaction containers

        if "transactions" in raw:

            rows = raw["transactions"]

        elif "data" in raw:

            rows = raw["data"]

        elif "accounts" in raw:

            for account in raw["accounts"]:

                account_id = account.get(
                    "account_id"
                )

                timeline = account.get(
                    "timeline",
                    []
                )

                for item in timeline:

                    transaction = item.get(
                        "transaction",
                        item
                    )

                    if isinstance(transaction, dict):

                        row = transaction.copy()

                        row["account_id"] = (
                            account_id
                        )

                        row["phase"] = (
                            item.get("phase")
                        )

                        row["day"] = (
                            item.get("day")
                        )

                        row["sequence"] = (
                            item.get("sequence")
                        )

                        rows.append(row)

    if not rows:

        raise ValueError(
            "Could not extract transactions "
            "from Forge JSON."
        )

    df = pd.DataFrame(rows)

    print(
        f"Forge rows: {len(df)}"
    )

    print("\nForge columns:")
    print(df.columns.tolist())

    return df


# ============================================================
# CREATE FORGE FEATURES
# ============================================================

def create_forge_features(df):

    print("\nCreating Forge features...")

    data = df.copy()

    # --------------------------------------------------------
    # Required numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "amount",
        "step",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    ]

    for col in numeric_columns:

        if col not in data.columns:

            data[col] = 0.0

        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        ).fillna(0.0)

    # --------------------------------------------------------
    # Required categorical fields
    # --------------------------------------------------------

    if "type" not in data.columns:

        data["type"] = "UNKNOWN"

    if "account_id" not in data.columns:

        raise ValueError(
            "Forge data missing account_id"
        )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    data = data.sort_values(
        ["account_id", "step"]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    data["transaction_amount"] = (
        data["amount"]
    )

    # --------------------------------------------------------
    # Account age
    # --------------------------------------------------------

    account_min = (
        data.groupby("account_id")[
            "step"
        ].transform("min")
    )

    account_max = (
        data.groupby("account_id")[
            "step"
        ].transform("max")
    )

    data["account_age"] = (
        account_max -
        account_min
    )

    # --------------------------------------------------------
    # Transaction count
    # --------------------------------------------------------

    data["transaction_count"] = (
        data.groupby("account_id")
        .cumcount()
    )

    # --------------------------------------------------------
    # Historical amount statistics
    # --------------------------------------------------------

    previous_amount = (
        data.groupby("account_id")[
            "transaction_amount"
        ].shift(1)
    )

    previous_group = (
        previous_amount
        .groupby(data["account_id"])
    )

    data["avg_transaction_amount"] = (
        previous_group.transform("mean")
    )

    data["std_transaction_amount"] = (
        previous_group.transform("std")
    )

    data["max_transaction_amount"] = (
        previous_group.transform("max")
    )

    # --------------------------------------------------------
    # Time gap
    # --------------------------------------------------------

    previous_step = (
        data.groupby("account_id")[
            "step"
        ].shift(1)
    )

    data["time_gap"] = (
        data["step"] -
        previous_step
    )

    previous_gap = (
        data.groupby("account_id")[
            "time_gap"
        ].shift(1)
    )

    gap_group = (
        previous_gap
        .groupby(data["account_id"])
    )

    data["avg_time_gap"] = (
        gap_group.transform("mean")
    )

    data["std_time_gap"] = (
        gap_group.transform("std")
    )

    # --------------------------------------------------------
    # Transaction type
    # --------------------------------------------------------

    transaction_type = (
        data["type"]
        .astype(str)
        .str.upper()
    )

    data["is_cash_out"] = (
        transaction_type
        .eq("CASH_OUT")
        .astype(int)
    )

    data["is_payment"] = (
        transaction_type
        .eq("PAYMENT")
        .astype(int)
    )

    data["is_transfer"] = (
        transaction_type
        .eq("TRANSFER")
        .astype(int)
    )

    data["is_debit"] = (
        transaction_type
        .eq("DEBIT")
        .astype(int)
    )

    # --------------------------------------------------------
    # Historical transaction-type ratios
    # --------------------------------------------------------

    ratio_columns = [
        (
            "is_cash_out",
            "cash_out_ratio"
        ),
        (
            "is_payment",
            "payment_ratio"
        ),
        (
            "is_transfer",
            "transfer_ratio"
        ),
        (
            "is_debit",
            "debit_ratio"
        ),
    ]

    for source, target in ratio_columns:

        previous = (
            data.groupby("account_id")[
                source
            ].shift(1)
        )

        data[target] = (
            previous
            .groupby(data["account_id"])
            .transform("mean")
        )

    # --------------------------------------------------------
    # Final features
    # --------------------------------------------------------

    features = data[
        ML_FEATURES
    ].copy()

    features = features.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Use sensible fallbacks
    features[
        "avg_transaction_amount"
    ] = features[
        "avg_transaction_amount"
    ].fillna(
        features[
            "transaction_amount"
        ].median()
    )

    features[
        "max_transaction_amount"
    ] = features[
        "max_transaction_amount"
    ].fillna(
        features[
            "transaction_amount"
        ].median()
    )

    features[
        "std_transaction_amount"
    ] = features[
        "std_transaction_amount"
    ].fillna(0.0)

    features[
        "avg_time_gap"
    ] = features[
        "avg_time_gap"
    ].fillna(
        features[
            "avg_time_gap"
        ].median()
    )

    features[
        "std_time_gap"
    ] = features[
        "std_time_gap"
    ].fillna(0.0)

    features = features.fillna(0.0)

    return features


# ============================================================
# LOAD MODELS
# ============================================================

def load_models():

    print("\n" + "=" * 60)
    print("LOADING MODELS")
    print("=" * 60)

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    print("\nLoading XGBoost...")

    if not os.path.exists(
        XGB_MODEL_PATH
    ):

        raise FileNotFoundError(
            f"XGBoost model not found:\n"
            f"{XGB_MODEL_PATH}"
        )

    xgb_model = joblib.load(
        XGB_MODEL_PATH
    )

    print(
        "XGBoost loaded successfully."
    )

    # --------------------------------------------------------
    # Isolation Forest
    # --------------------------------------------------------

    print(
        "\nLoading Isolation Forest..."
    )

    if not os.path.exists(
        IF_MODEL_PATH
    ):

        raise FileNotFoundError(
            f"Isolation Forest model not found:\n"
            f"{IF_MODEL_PATH}"
        )

    if not os.path.exists(
        IF_SCALER_PATH
    ):

        raise FileNotFoundError(
            f"Isolation Forest scaler not found:\n"
            f"{IF_SCALER_PATH}"
        )

    if not os.path.exists(
        IF_THRESHOLD_PATH
    ):

        raise FileNotFoundError(
            f"Isolation Forest threshold not found:\n"
            f"{IF_THRESHOLD_PATH}"
        )

    if_model = joblib.load(
        IF_MODEL_PATH
    )

    scaler = joblib.load(
        IF_SCALER_PATH
    )

    threshold = joblib.load(
        IF_THRESHOLD_PATH
    )

    print(
        "Isolation Forest loaded successfully."
    )

    return (
        xgb_model,
        if_model,
        scaler,
        threshold
    )


# ============================================================
# NORMALIZE ANOMALY SCORE
# ============================================================

def normalize_anomaly_score(
    raw_scores,
    threshold
):

    """
    Convert Isolation Forest scores
    into approximately 0-1 anomaly scores.

    Higher = more anomalous.
    """

    scores = np.asarray(
        raw_scores,
        dtype=float
    )

    # --------------------------------------------------------
    # We use the threshold as the reference point.
    #
    # Values around/below threshold:
    #     low anomaly risk
    #
    # Values above threshold:
    #     higher anomaly risk
    # --------------------------------------------------------

    scale = np.std(scores)

    if scale < 1e-8:

        scale = 1.0

    normalized = (
        scores - threshold
    ) / scale

    # Sigmoid
    normalized = (
        1.0 /
        (
            1.0 +
            np.exp(-normalized)
        )
    )

    return normalized


# ============================================================
# FUSION
# ============================================================

def calculate_fusion(
    xgb_scores,
    anomaly_scores
):

    """
    Combine Layer 1 and Layer 2.

    XGBoost gets more weight because it is
    the supervised fraud detector.

    Isolation Forest provides behavioral
    novelty information.
    """

    XGB_WEIGHT = 0.70
    ANOMALY_WEIGHT = 0.30

    final_score = (
        XGB_WEIGHT *
        xgb_scores
        +
        ANOMALY_WEIGHT *
        anomaly_scores
    )

    return final_score


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_risk(score):

    if score >= 0.70:

        return "FRAUD"

    elif score >= 0.30:

        return "SUSPICIOUS"

    else:

        return "NORMAL"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("VERITRACE - LAYER 3")
    print("XGBOOST + ISOLATION FOREST RISK FUSION")
    print("=" * 60)

    # --------------------------------------------------------
    # Load models
    # --------------------------------------------------------

    (
        xgb_model,
        if_model,
        scaler,
        if_threshold
    ) = load_models()

    # --------------------------------------------------------
    # Load Forge
    # --------------------------------------------------------

    forge_df = load_forge_data(
        FORGE_PATH
    )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    features = create_forge_features(
        forge_df
    )

    print(
        f"\nFeature shape: "
        f"{features.shape}"
    )

    print(
        "\nFeature order:"
    )

    print(
        features.columns.tolist()
    )

    # --------------------------------------------------------
    # Verify feature order
    # --------------------------------------------------------

    if list(features.columns) != ML_FEATURES:

        raise ValueError(
            "Feature order mismatch."
        )

    # --------------------------------------------------------
    # Layer 1
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LAYER 1 - XGBOOST")
    print("=" * 60)

    xgb_scores = (
        xgb_model.predict_proba(
            features
        )[:, 1]
    )

    print(
        f"Mean fraud score: "
        f"{xgb_scores.mean():.6f}"
    )

    print(
        f"Maximum fraud score: "
        f"{xgb_scores.max():.6f}"
    )

    # --------------------------------------------------------
    # Layer 2
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LAYER 2 - ISOLATION FOREST")
    print("=" * 60)

    scaled_features = scaler.transform(
        features
    )

    raw_anomaly_scores = (
        if_model.decision_function(
            scaled_features
        )
    )

    anomaly_scores = (
        normalize_anomaly_score(
            raw_anomaly_scores,
            if_threshold
        )
    )

    print(
        f"Mean anomaly score: "
        f"{anomaly_scores.mean():.6f}"
    )

    print(
        f"Maximum anomaly score: "
        f"{anomaly_scores.max():.6f}"
    )

    # --------------------------------------------------------
    # Layer 3
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LAYER 3 - RISK FUSION")
    print("=" * 60)

    final_scores = calculate_fusion(
        xgb_scores,
        anomaly_scores
    )

    risk_labels = [
        classify_risk(score)
        for score in final_scores
    ]

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    results = pd.DataFrame({

        "account_id":
            forge_df[
                "account_id"
            ].values,

        "phase":
            forge_df.get(
                "phase",
                pd.Series(
                    ["UNKNOWN"] *
                    len(forge_df)
                )
            ).values,

        "attack_type":
            forge_df.get(
                "attack_type",
                pd.Series(
                    [None] *
                    len(forge_df)
                )
            ).values,

        "xgb_fraud_score":
            xgb_scores,

        "anomaly_score":
            anomaly_scores,

        "final_risk_score":
            final_scores,

        "risk_label":
            risk_labels,
    })

    # --------------------------------------------------------
    # Prediction distribution
    # --------------------------------------------------------

    print(
        "\nRisk distribution:"
    )

    print(
        results[
            "risk_label"
        ].value_counts()
    )

    # --------------------------------------------------------
    # Score statistics
    # --------------------------------------------------------

    print(
        "\nFinal risk score statistics:"
    )

    print(
        results[
            "final_risk_score"
        ].describe()
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True
    )

    output_path = os.path.join(
        RESULTS_DIR,
        "forge_risk_fusion_predictions.csv"
    )

    results.to_csv(
        output_path,
        index=False
    )

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("FORGE EVALUATION")
    print("=" * 60)

    # IMPORTANT:
    #
    # Only ATTACK phase is treated as
    # positive for this evaluation.
    #
    # Other phases are not automatically
    # treated as fraud.
    # --------------------------------------------------------

    if "phase" in forge_df.columns:

        actual = (
            forge_df[
                "phase"
            ]
            .astype(str)
            .str.upper()
            .eq("ATTACK")
            .astype(int)
        )

        print(
            "\nActual labels:"
        )

        print(
            actual.value_counts()
        )

        if actual.nunique() == 2:

            auc = roc_auc_score(
                actual,
                final_scores
            )

            print(
                f"\nROC-AUC: {auc:.4f}"
            )

            # ------------------------------------------------
            # Evaluation at several thresholds
            # ------------------------------------------------

            for threshold in [
                0.30,
                0.40,
                0.50,
                0.60,
                0.70,
                0.80,
            ]:

                predicted = (
                    final_scores >=
                    threshold
                ).astype(int)

                cm = confusion_matrix(
                    actual,
                    predicted
                )

                report = classification_report(
                    actual,
                    predicted,
                    target_names=[
                        "NORMAL",
                        "FORGE_ATTACK"
                    ],
                    zero_division=0
                )

                print(
                    "\n" +
                    "-" * 60
                )

                print(
                    f"Threshold: "
                    f"{threshold:.2f}"
                )

                print(
                    "Confusion matrix:"
                )

                print(cm)

                print(
                    "\nClassification report:"
                )

                print(report)

    # --------------------------------------------------------
    # Show sample
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("FIRST 20 RESULTS")
    print("=" * 60)

    print(
        results.head(20).to_string(
            index=False
        )
    )

    print("\n" + "=" * 60)
    print("LAYER 3 COMPLETE")
    print("=" * 60)

    print(
        "\nResults saved to:"
    )

    print(
        output_path
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()