import os
import sys
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    confusion_matrix,
    classification_report
)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

BENCHMARK_PATH = os.path.join(
    DATA_DIR,
    "transactions_train.csv"
)

FORGE_PATH = os.path.join(
    DATA_DIR,
    "generated",
    "batch_attack_timeline.json"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_anomaly_model.joblib"
)

SCALER_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_scaler.joblib"
)

THRESHOLD_PATH = os.path.join(
    MODEL_DIR,
    "isolation_forest_threshold.joblib"
)

OUTPUT_PATH = os.path.join(
    RESULTS_DIR,
    "forge_anomaly_predictions.csv"
)


# ------------------------------------------------------------
# FEATURES
# ------------------------------------------------------------

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
# BENCHMARK FEATURE CREATION
# ============================================================

def create_benchmark_features(df):

    data = df.copy()

    print("\nBenchmark raw shape:", data.shape)

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required = [
        "transaction_amount",
        "account_age_days",
        "customer_id",
        "transaction_time",
        "payment_channel",
    ]

    for col in required:
        if col not in data.columns:
            raise ValueError(
                f"Benchmark dataset missing required column: {col}"
            )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    data["transaction_amount"] = pd.to_numeric(
        data["transaction_amount"],
        errors="coerce"
    ).fillna(0)

    data["account_age_days"] = pd.to_numeric(
        data["account_age_days"],
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------

    data["transaction_time"] = pd.to_datetime(
        data["transaction_time"],
        errors="coerce"
    )

    data = data.sort_values(
        ["customer_id", "transaction_time"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Basic features
    # --------------------------------------------------------

    data["transaction_amount"] = data[
        "transaction_amount"
    ]

    data["account_age"] = data[
        "account_age_days"
    ]

    data["transaction_count"] = (
        data.groupby("customer_id")
        .cumcount()
    )

    # --------------------------------------------------------
    # Historical amount
    # --------------------------------------------------------

    previous_amount = (
        data.groupby("customer_id")[
            "transaction_amount"
        ].shift(1)
    )

    data["avg_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("mean")
    )

    data["std_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("std")
    )

    data["max_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("max")
    )

    global_mean = data[
        "transaction_amount"
    ].mean()

    data["avg_transaction_amount"] = (
        data["avg_transaction_amount"]
        .fillna(global_mean)
    )

    data["std_transaction_amount"] = (
        data["std_transaction_amount"]
        .fillna(0)
    )

    data["max_transaction_amount"] = (
        data["max_transaction_amount"]
        .fillna(global_mean)
    )

    # --------------------------------------------------------
    # Time gap
    # --------------------------------------------------------

    previous_time = (
        data.groupby("customer_id")[
            "transaction_time"
        ].shift(1)
    )

    data["time_gap"] = (
        data["transaction_time"]
        - previous_time
    ).dt.total_seconds() / 3600

    data["time_gap"] = data[
        "time_gap"
    ].fillna(0)

    data["avg_time_gap"] = (
        data.groupby("customer_id")[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
    )

    data["std_time_gap"] = (
        data.groupby("customer_id")[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .std()
        )
    )

    data["avg_time_gap"] = (
        data["avg_time_gap"]
        .fillna(data["time_gap"].median())
    )

    data["std_time_gap"] = (
        data["std_time_gap"]
        .fillna(0)
    )

    # --------------------------------------------------------
    # Payment channel
    # --------------------------------------------------------

    channel = (
        data["payment_channel"]
        .astype(str)
        .str.upper()
    )

    data["is_cash_out"] = (
        channel.str.contains("CASH")
        .astype(int)
    )

    data["is_payment"] = (
        channel.str.contains("PAYMENT")
        .astype(int)
    )

    data["is_transfer"] = (
        channel.str.contains("TRANSFER")
        .astype(int)
    )

    data["is_debit"] = (
        channel.str.contains("DEBIT")
        .astype(int)
    )

    for source, target in [
        ("is_cash_out", "cash_out_ratio"),
        ("is_payment", "payment_ratio"),
        ("is_transfer", "transfer_ratio"),
        ("is_debit", "debit_ratio"),
    ]:

        data[target] = (
            data.groupby("customer_id")[source]
            .transform(
                lambda x:
                x.shift(1)
                .expanding()
                .mean()
            )
            .fillna(0)
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

    features = features.fillna(0)

    return features


# ============================================================
# FORGE LOADING
# ============================================================

def load_forge_data(path):

    import json

    with open(path, "r") as f:
        raw = json.load(f)

    rows = []

    # --------------------------------------------------------
    # Expected Forge structure:
    #
    # account_id
    # timeline
    # --------------------------------------------------------

    if isinstance(raw, list):

        accounts = raw

    elif isinstance(raw, dict):

        if "accounts" in raw:
            accounts = raw["accounts"]

        elif "data" in raw:
            accounts = raw["data"]

        else:
            accounts = [raw]

    else:
        raise ValueError("Unsupported Forge JSON format")

    for account in accounts:

        if not isinstance(account, dict):
            continue

        account_id = account.get(
            "account_id",
            "UNKNOWN"
        )

        timeline = account.get(
            "timeline",
            []
        )

        for item in timeline:

            if not isinstance(item, dict):
                continue

            transaction = item.get(
                "transaction",
                {}
            )

            if not isinstance(transaction, dict):
                continue

            row = transaction.copy()

            row["step"] = item.get(
                "step",
                row.get("step", 0)
            )

            row["day"] = item.get(
                "day",
                row.get("day", 0)
            )

            row["sequence"] = item.get(
                "sequence",
                0
            )

            row["phase"] = item.get(
                "phase",
                "NORMAL"
            )

            row["account_id"] = account_id

            rows.append(row)

    df = pd.DataFrame(rows)

    return df


# ============================================================
# FORGE FEATURES
# ============================================================

def create_forge_features(df):

    data = df.copy()

    print("\nRaw Forge columns:")
    print(data.columns.tolist())

    # --------------------------------------------------------
    # Numeric
    # --------------------------------------------------------

    for col in [
        "amount",
        "step",
        "oldbalanceOrg",
        "newbalanceOrig",
    ]:

        if col not in data.columns:
            data[col] = 0

        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # Account ID
    # --------------------------------------------------------

    if "account_id" not in data.columns:
        data["account_id"] = "UNKNOWN"

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    data = data.sort_values(
        ["account_id", "step"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    data["transaction_amount"] = (
        data["amount"]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # account_age is based on actual available Forge
    # timeline rather than benchmark assumptions.
    # --------------------------------------------------------

    data["account_age"] = (
        data.groupby("account_id")["step"]
        .transform("max")
        -
        data.groupby("account_id")["step"]
        .transform("min")
    )

    data["transaction_count"] = (
        data.groupby("account_id")
        .cumcount()
    )

    # --------------------------------------------------------
    # Historical amounts
    # --------------------------------------------------------

    previous_amount = (
        data.groupby("account_id")[
            "transaction_amount"
        ].shift(1)
    )

    data["avg_transaction_amount"] = (
        previous_amount
        .groupby(data["account_id"])
        .transform("mean")
    )

    data["std_transaction_amount"] = (
        previous_amount
        .groupby(data["account_id"])
        .transform("std")
    )

    data["max_transaction_amount"] = (
        previous_amount
        .groupby(data["account_id"])
        .transform("max")
    )

    global_mean = (
        data["transaction_amount"].mean()
    )

    data["avg_transaction_amount"] = (
        data["avg_transaction_amount"]
        .fillna(global_mean)
    )

    data["std_transaction_amount"] = (
        data["std_transaction_amount"]
        .fillna(0)
    )

    data["max_transaction_amount"] = (
        data["max_transaction_amount"]
        .fillna(global_mean)
    )

    # --------------------------------------------------------
    # Time gaps
    # --------------------------------------------------------

    previous_step = (
        data.groupby("account_id")[
            "step"
        ].shift(1)
    )

    data["time_gap"] = (
        data["step"] - previous_step
    )

    data["avg_time_gap"] = (
        data.groupby("account_id")[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
    )

    data["std_time_gap"] = (
        data.groupby("account_id")[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .std()
        )
    )

    data["avg_time_gap"] = (
        data["avg_time_gap"]
        .fillna(
            data["time_gap"].median()
        )
    )

    data["std_time_gap"] = (
        data["std_time_gap"]
        .fillna(0)
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
    # Ratios
    # --------------------------------------------------------

    for source, target in [
        ("is_cash_out", "cash_out_ratio"),
        ("is_payment", "payment_ratio"),
        ("is_transfer", "transfer_ratio"),
        ("is_debit", "debit_ratio"),
    ]:

        data[target] = (
            data.groupby("account_id")[source]
            .transform(
                lambda x:
                x.shift(1)
                .expanding()
                .mean()
            )
            .fillna(0)
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    features = data[
        ML_FEATURES
    ].copy()

    features = features.replace(
        [np.inf, -np.inf],
        np.nan
    )

    features = features.fillna(0)

    return features


# ============================================================
# TRAIN LAYER 2
# ============================================================

def train_anomaly_detector():

    print("=" * 60)
    print("VERITRACE - LAYER 2")
    print("ISOLATION FOREST ANOMALY DETECTION")
    print("=" * 60)

    # ========================================================
    # BENCHMARK
    # ========================================================

    print("\n" + "=" * 60)
    print("LOADING BENCHMARK DATA")
    print("=" * 60)

    benchmark = pd.read_csv(
        BENCHMARK_PATH
    )

    print(
        "Benchmark shape:",
        benchmark.shape
    )

    benchmark_features = (
        create_benchmark_features(
            benchmark
        )
    )

    # --------------------------------------------------------
    # Only genuine benchmark transactions
    # --------------------------------------------------------

    if "is_fraud" in benchmark.columns:

        normal_mask = (
            benchmark["is_fraud"] == 0
        )

        benchmark_normal = (
            benchmark_features.loc[
                normal_mask
            ]
        )

    else:

        benchmark_normal = (
            benchmark_features
        )

    print(
        "Benchmark normal rows:",
        len(benchmark_normal)
    )

    # ========================================================
    # FORGE
    # ========================================================

    print("\n" + "=" * 60)
    print("LOADING FORGE DATA")
    print("=" * 60)

    forge = load_forge_data(
        FORGE_PATH
    )

    print(
        "Forge rows:",
        len(forge)
    )

    print("\nForge phases:")
    print(
        forge["phase"]
        .value_counts()
    )

    forge_features = (
        create_forge_features(
            forge
        )
    )

    # --------------------------------------------------------
    # CRITICAL CHANGE
    #
    # Train only on Forge behavior that is NOT an attack.
    #
    # ATTACK and POST_ATTACK are excluded.
    # --------------------------------------------------------

    normal_phases = [
        "NORMAL",
        "DORMANT",
        "ACTIVATION"
    ]

    forge_normal_mask = (
        forge["phase"]
        .astype(str)
        .str.upper()
        .isin(normal_phases)
    )

    forge_normal_features = (
        forge_features.loc[
            forge_normal_mask
        ]
    )

    print(
        "\nForge normal training rows:",
        len(forge_normal_features)
    )

    print(
        "Forge attack rows excluded:",
        len(forge) -
        len(forge_normal_features)
    )

    # ========================================================
    # COMBINE NORMAL DATA
    # ========================================================

    training_features = pd.concat(
        [
            benchmark_normal,
            forge_normal_features
        ],
        ignore_index=True
    )

    training_features = (
        training_features
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )

    print("\n" + "=" * 60)
    print("COMBINED NORMAL TRAINING DATA")
    print("=" * 60)

    print(
        "Training shape:",
        training_features.shape
    )

    # ========================================================
    # SCALE
    # ========================================================

    print("\nScaling features...")

    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        training_features
    )

    # ========================================================
    # ISOLATION FOREST
    # ========================================================

    print("\n" + "=" * 60)
    print("TRAINING ISOLATION FOREST")
    print("=" * 60)

    model = IsolationForest(
        n_estimators=300,
        contamination="auto",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train
    )

    print(
        "Isolation Forest training complete."
    )

    # ========================================================
    # DETERMINE THRESHOLD
    # ========================================================

    # sklearn decision_function:
    # higher = more normal
    #
    # Convert to anomaly score:
    # higher = more anomalous
    # ========================================================

    train_normal_scores = -model.decision_function(
        X_train
    )

    # Use 99th percentile of normal behavior.
    threshold = np.percentile(
        train_normal_scores,
        99
    )

    print(
        "\nAnomaly threshold:",
        threshold
    )

    print(
        "Normal anomaly score range:"
    )

    print(
        "Minimum:",
        train_normal_scores.min()
    )

    print(
        "Maximum:",
        train_normal_scores.max()
    )

    print(
        "Mean:",
        train_normal_scores.mean()
    )

    # ========================================================
    # SAVE
    # ========================================================

    joblib.dump(
        model,
        MODEL_PATH
    )

    joblib.dump(
        scaler,
        SCALER_PATH
    )

    joblib.dump(
        threshold,
        THRESHOLD_PATH
    )

    print("\nModel saved:")
    print(MODEL_PATH)

    print("\nScaler saved:")
    print(SCALER_PATH)

    print("\nThreshold saved:")
    print(THRESHOLD_PATH)

    # ========================================================
    # EVALUATE FORGE
    # ========================================================

    print("\n" + "=" * 60)
    print("EVALUATING FORGE")
    print("=" * 60)

    X_forge = scaler.transform(
        forge_features
    )

    forge_scores = -model.decision_function(
        X_forge
    )

    # --------------------------------------------------------
    # Ground truth
    #
    # ATTACK + POST_ATTACK = attack
    # everything else = normal
    # --------------------------------------------------------

    y_true = (
        forge["phase"]
        .astype(str)
        .str.upper()
        .isin([
            "ATTACK",
            "POST_ATTACK"
        ])
        .astype(int)
    )

    predictions = (
        forge_scores >= threshold
    ).astype(int)

    print("\nActual labels:")
    print(
        pd.Series(y_true)
        .value_counts()
    )

    print("\nPredictions:")
    print(
        pd.Series(predictions)
        .value_counts()
    )

    # ========================================================
    # AUC
    # ========================================================

    try:

        auc = roc_auc_score(
            y_true,
            forge_scores
        )

        print(
            "\nROC-AUC:",
            round(auc, 4)
        )

    except Exception as e:

        print(
            "Could not calculate AUC:",
            e
        )

    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    cm = confusion_matrix(
        y_true,
        predictions
    )

    print(
        "\nConfusion matrix:"
    )

    print(cm)

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y_true,
            predictions,
            target_names=[
                "NORMAL",
                "FORGE_ATTACK"
            ],
            zero_division=0
        )
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    result = forge[
        [
            "account_id",
            "step",
            "phase"
        ]
    ].copy()

    result["actual_label"] = y_true

    result["anomaly_score"] = (
        forge_scores
    )

    result["anomaly_prediction"] = (
        predictions
    )

    result["anomaly_label"] = np.where(
        predictions == 1,
        "ANOMALY",
        "NORMAL"
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        "\nPredictions saved:"
    )

    print(
        OUTPUT_PATH
    )

    print("\n" + "=" * 60)
    print("LAYER 2 COMPLETE")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    train_anomaly_detector()