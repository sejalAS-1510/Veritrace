import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)

from xgboost import XGBClassifier

from forge_adapter import (
    load_forge_data,
    create_forge_features,
    ML_FEATURES,
)


# ============================================================
# PATHS
# ============================================================

# Current file:
# backend/sentinel/train_unified_xgboost.py
#
# BASE_DIR:
# backend/

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

GENERATED_DIR = os.path.join(
    DATA_DIR,
    "generated"
)

MODEL_DIR = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "models"
)

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# CORRECT DATA PATHS
# ============================================================

# backend/data/transactions_train.csv

BENCHMARK_PATH = os.path.join(
    DATA_DIR,
    "transactions_train.csv"
)


# backend/data/generated/batch_attack_timeline.json

FORGE_PATH = os.path.join(
    GENERATED_DIR,
    "batch_attack_timeline.json"
)


# Output model

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_unified_fraud_model.pkl"
)


# Output feature list

FEATURE_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_unified_fraud_model_features.json"
)


# ============================================================
# PRINT PATHS
# ============================================================

def print_paths():

    print("\n" + "=" * 60)
    print("PATH CONFIGURATION")
    print("=" * 60)

    print("\nBenchmark:")
    print(BENCHMARK_PATH)

    print("\nForge:")
    print(FORGE_PATH)

    print("\nModel:")
    print(MODEL_PATH)


# ============================================================
# LOAD BENCHMARK
# ============================================================

def load_benchmark_data():

    print("\n" + "=" * 60)
    print("LOADING BENCHMARK DATA")
    print("=" * 60)

    if not os.path.exists(BENCHMARK_PATH):

        raise FileNotFoundError(
            f"\nBenchmark file not found:\n{BENCHMARK_PATH}"
        )

    df = pd.read_csv(
        BENCHMARK_PATH
    )

    print(
        "\nBenchmark shape:",
        df.shape
    )

    print(
        "\nBenchmark columns:"
    )

    print(
        df.columns.tolist()
    )

    return df


# ============================================================
# FIND BENCHMARK LABEL
# ============================================================

def find_label_column(df):

    possible_labels = [
        "is_fraud",
        "isFraud",
        "fraud",
        "label"
    ]

    for column in possible_labels:

        if column in df.columns:
            return column

    raise ValueError(
        "\nCould not find fraud label column.\n"
        f"Expected one of: {possible_labels}"
    )


# ============================================================
# BENCHMARK FEATURE ENGINEERING
# ============================================================

def create_benchmark_features(df):

    """
    Convert Digital Payment Fraud Detection Benchmark
    into the SAME 12-feature space used by Forge.

    IMPORTANT:
    No 'step' column is required.
    The benchmark uses transaction_time.
    """

    data = df.copy()

    print(
        "\nBenchmark raw shape:",
        data.shape
    )

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required = [
        "customer_id",
        "transaction_time",
        "account_age_days",
        "transaction_amount",
        "payment_channel",
    ]

    missing = [
        col
        for col in required
        if col not in data.columns
    ]

    if missing:

        raise ValueError(
            "\nBenchmark dataset is missing columns:\n"
            + str(missing)
        )

    # --------------------------------------------------------
    # NUMERIC CONVERSION
    # --------------------------------------------------------

    numeric_columns = [
        "transaction_amount",
        "account_age_days",
    ]

    for col in numeric_columns:

        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    data["transaction_time"] = pd.to_datetime(
        data["transaction_time"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # REMOVE INVALID ROWS
    # --------------------------------------------------------

    data = data.dropna(
        subset=[
            "customer_id",
            "transaction_time",
            "transaction_amount",
        ]
    ).copy()

    # --------------------------------------------------------
    # SORT BY CUSTOMER + TIME
    # --------------------------------------------------------

    data = data.sort_values(
        [
            "customer_id",
            "transaction_time"
        ]
    ).reset_index(
        drop=True
    )

    # ========================================================
    # 1. TRANSACTION AMOUNT
    # ========================================================

    data["transaction_amount"] = (
        data["transaction_amount"]
        .astype(float)
    )

    # ========================================================
    # 2. ACCOUNT AGE
    # ========================================================

    data["account_age"] = (
        data["account_age_days"]
        .astype(float)
    )

    # ========================================================
    # 3. HISTORICAL TRANSACTION COUNT
    # ========================================================

    data["transaction_count"] = (
        data
        .groupby("customer_id")
        .cumcount()
        .astype(float)
    )

    # ========================================================
    # HISTORICAL AMOUNT
    # ========================================================

    previous_amount = (
        data
        .groupby("customer_id")
        ["transaction_amount"]
        .shift(1)
    )

    # ========================================================
    # 4. AVERAGE HISTORICAL AMOUNT
    # ========================================================

    data["avg_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("mean")
    )

    # ========================================================
    # 5. HISTORICAL AMOUNT STD
    # ========================================================

    data["std_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("std")
    )

    # ========================================================
    # 6. HISTORICAL MAX AMOUNT
    # ========================================================

    data["max_transaction_amount"] = (
        previous_amount
        .groupby(data["customer_id"])
        .transform("max")
    )

    # --------------------------------------------------------
    # FALLBACK VALUES
    # --------------------------------------------------------

    global_mean = (
        data["transaction_amount"]
        .mean()
    )

    if pd.isna(global_mean):
        global_mean = 0.0

    data["avg_transaction_amount"] = (
        data["avg_transaction_amount"]
        .fillna(global_mean)
    )

    data["std_transaction_amount"] = (
        data["std_transaction_amount"]
        .fillna(0.0)
    )

    data["max_transaction_amount"] = (
        data["max_transaction_amount"]
        .fillna(global_mean)
    )

    # ========================================================
    # TIME GAPS
    # ========================================================

    previous_time = (
        data
        .groupby("customer_id")
        ["transaction_time"]
        .shift(1)
    )

    data["time_gap"] = (
        data["transaction_time"]
        - previous_time
    ).dt.total_seconds() / 3600.0

    # ========================================================
    # 7. AVERAGE TIME GAP
    # ========================================================

    previous_gap = (
        data
        .groupby("customer_id")
        ["time_gap"]
        .shift(1)
    )

    data["avg_time_gap"] = (
        previous_gap
        .groupby(data["customer_id"])
        .transform("mean")
    )

    # ========================================================
    # 8. STD TIME GAP
    # ========================================================

    data["std_time_gap"] = (
        previous_gap
        .groupby(data["customer_id"])
        .transform("std")
    )

    global_gap = (
        data["time_gap"]
        .median()
    )

    if pd.isna(global_gap):
        global_gap = 0.0

    data["avg_time_gap"] = (
        data["avg_time_gap"]
        .fillna(global_gap)
    )

    data["std_time_gap"] = (
        data["std_time_gap"]
        .fillna(0.0)
    )

    # ========================================================
    # TRANSACTION TYPE
    # ========================================================

    transaction_type = (
        data["payment_channel"]
        .astype(str)
        .str.upper()
    )

    # --------------------------------------------------------
    # Map payment channels into approximate transaction types
    # --------------------------------------------------------

    data["is_cash_out"] = (
        transaction_type
        .str.contains(
            "CASH|WITHDRAW",
            na=False
        )
        .astype(int)
    )

    data["is_payment"] = (
        transaction_type
        .str.contains(
            "PAYMENT|CARD|UPI|ONLINE|POS",
            na=False
        )
        .astype(int)
    )

    data["is_transfer"] = (
        transaction_type
        .str.contains(
            "TRANSFER|BANK",
            na=False
        )
        .astype(int)
    )

    data["is_debit"] = (
        transaction_type
        .str.contains(
            "DEBIT",
            na=False
        )
        .astype(int)
    )

    # ========================================================
    # 9. CASH-OUT RATIO
    # ========================================================

    data["cash_out_ratio"] = (
        data
        .groupby("customer_id")
        ["is_cash_out"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
        .fillna(0.0)
    )

    # ========================================================
    # 10. PAYMENT RATIO
    # ========================================================

    data["payment_ratio"] = (
        data
        .groupby("customer_id")
        ["is_payment"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
        .fillna(0.0)
    )

    # ========================================================
    # 11. TRANSFER RATIO
    # ========================================================

    data["transfer_ratio"] = (
        data
        .groupby("customer_id")
        ["is_transfer"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
        .fillna(0.0)
    )

    # ========================================================
    # 12. DEBIT RATIO
    # ========================================================

    data["debit_ratio"] = (
        data
        .groupby("customer_id")
        ["is_debit"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
        .fillna(0.0)
    )

    # ========================================================
    # FINAL FEATURES
    # ========================================================

    features = data[
        ML_FEATURES
    ].copy()

    # --------------------------------------------------------
    # CLEAN NUMERICAL VALUES
    # --------------------------------------------------------

    features = features.replace(
        [np.inf, -np.inf],
        np.nan
    )

    features = features.fillna(
        0.0
    )

    # --------------------------------------------------------
    # FORCE FLOAT
    # --------------------------------------------------------

    features = features.astype(
        float
    )

    print(
        "\nBenchmark feature shape:",
        features.shape
    )

    print(
        "\nBenchmark feature columns:"
    )

    print(
        features.columns.tolist()
    )

    return features, data.index


# ============================================================
# FORGE LABEL EXTRACTION
# ============================================================

def extract_forge_labels(df):

    """
    Forge format:

    transaction = {
        ...
        "is_attack": True/False
    }

    True  -> 1
    False -> 0
    """

    labels = []

    for value in df["transaction"]:

        if isinstance(value, dict):

            labels.append(
                int(
                    bool(
                        value.get(
                            "is_attack",
                            False
                        )
                    )
                )
            )

        else:

            labels.append(0)

    return np.array(
        labels,
        dtype=int
    )


# ============================================================
# LOAD FORGE
# ============================================================

def load_forge_dataset():

    print("\n" + "=" * 60)
    print("LOADING FORGE DATA")
    print("=" * 60)

    if not os.path.exists(FORGE_PATH):

        raise FileNotFoundError(
            f"\nForge file not found:\n{FORGE_PATH}"
        )

    forge = load_forge_data(
        FORGE_PATH
    )

    print(
        "\nForge shape:",
        forge.shape
    )

    print(
        "\nForge columns:"
    )

    print(
        forge.columns.tolist()
    )

    return forge


# ============================================================
# TRAINING DATA SUMMARY
# ============================================================

def print_dataset_summary(
    name,
    y
):

    print(
        f"\n{name} label distribution:"
    )

    print(
        pd.Series(y)
        .value_counts()
        .sort_index()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("UNIFIED XGBOOST FRAUD DETECTOR")
    print("=" * 60)

    print_paths()

    # ========================================================
    # LOAD BENCHMARK
    # ========================================================

    benchmark = (
        load_benchmark_data()
    )

    # ========================================================
    # BENCHMARK LABEL
    # ========================================================

    label_column = (
        find_label_column(
            benchmark
        )
    )

    print(
        "\nBenchmark label column:",
        label_column
    )

    # ========================================================
    # CREATE BENCHMARK FEATURES
    # ========================================================

    print(
        "\nCreating benchmark features..."
    )

    X_benchmark, valid_indices = (
        create_benchmark_features(
            benchmark
        )
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # create_benchmark_features removes invalid rows.
    # Therefore labels must use the same remaining rows.
    # --------------------------------------------------------

    y_benchmark = (
        pd.to_numeric(
            benchmark.loc[
                valid_indices,
                label_column
            ],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
        .values
    )

    # Safety check

    if len(X_benchmark) != len(
        y_benchmark
    ):

        raise ValueError(
            "\nBenchmark feature/label "
            "length mismatch:\n"
            f"Features: {len(X_benchmark)}\n"
            f"Labels: {len(y_benchmark)}"
        )

    print_dataset_summary(
        "Benchmark",
        y_benchmark
    )

    # ========================================================
    # LOAD FORGE
    # ========================================================

    forge = (
        load_forge_dataset()
    )

    # ========================================================
    # FORGE LABELS
    # ========================================================

    y_forge = (
        extract_forge_labels(
            forge
        )
    )

    print_dataset_summary(
        "Forge",
        y_forge
    )

    # ========================================================
    # FORGE FEATURES
    # ========================================================

    print(
        "\nCreating Forge features..."
    )

    X_forge = (
        create_forge_features(
            forge
        )
    )

    X_forge = X_forge[
        ML_FEATURES
    ].copy()

    X_forge = X_forge.replace(
        [np.inf, -np.inf],
        np.nan
    )

    X_forge = X_forge.fillna(
        0.0
    )

    X_forge = X_forge.astype(
        float
    )

    print(
        "\nForge feature shape:",
        X_forge.shape
    )

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if len(X_forge) != len(
        y_forge
    ):

        raise ValueError(
            "\nForge feature/label "
            "length mismatch:\n"
            f"Features: {len(X_forge)}\n"
            f"Labels: {len(y_forge)}"
        )

    # ========================================================
    # CHECK FEATURE ORDER
    # ========================================================

    print(
        "\nExpected feature order:"
    )

    print(
        ML_FEATURES
    )

    if list(X_benchmark.columns) != list(
        X_forge.columns
    ):

        raise ValueError(
            "\nBenchmark and Forge "
            "feature columns do not match."
        )

    # ========================================================
    # COMBINE DATASETS
    # ========================================================

    print("\n" + "=" * 60)
    print("COMBINING BENCHMARK + FORGE")
    print("=" * 60)

    X = pd.concat(
        [
            X_benchmark,
            X_forge
        ],
        ignore_index=True
    )

    y = np.concatenate(
        [
            y_benchmark,
            y_forge
        ]
    )

    print(
        "\nFinal feature matrix:",
        X.shape
    )

    print(
        "\nFinal label distribution:"
    )

    print(
        pd.Series(y)
        .value_counts()
        .sort_index()
    )

    # ========================================================
    # CLEAN
    # ========================================================

    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    )

    X = X.fillna(
        0.0
    )

    X = X.astype(
        float
    )

    # ========================================================
    # FINAL SAFETY CHECKS
    # ========================================================

    if X.isna().any().any():

        raise ValueError(
            "NaN values remain in X."
        )

    if not np.isfinite(
        X.values
    ).all():

        raise ValueError(
            "Infinity values remain in X."
        )

    if len(X) != len(y):

        raise ValueError(
            "\nFinal X/y length mismatch."
        )

    # ========================================================
    # TRAIN / TEST SPLIT
    # ========================================================

    print("\n" + "=" * 60)
    print("TRAIN / TEST SPLIT")
    print("=" * 60)

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y
        )
    )

    print(
        "\nTraining shape:",
        X_train.shape
    )

    print(
        "Testing shape:",
        X_test.shape
    )

    # ========================================================
    # CLASS IMBALANCE
    # ========================================================

    negative = np.sum(
        y_train == 0
    )

    positive = np.sum(
        y_train == 1
    )

    if positive == 0:

        raise ValueError(
            "No fraud samples found."
        )

    scale_pos_weight = (
        negative / positive
    )

    print(
        "\nNormal training samples:",
        negative
    )

    print(
        "Fraud training samples:",
        positive
    )

    print(
        "scale_pos_weight:",
        scale_pos_weight
    )

    # ========================================================
    # TRAIN XGBOOST
    # ========================================================

    print("\n" + "=" * 60)
    print("TRAINING UNIFIED XGBOOST")
    print("=" * 60)

    model = XGBClassifier(

        n_estimators=400,

        max_depth=6,

        learning_rate=0.05,

        subsample=0.8,

        colsample_bytree=0.8,

        objective="binary:logistic",

        eval_metric="auc",

        scale_pos_weight=scale_pos_weight,

        random_state=42,

        n_jobs=-1,

        tree_method="hist"
    )

    model.fit(

        X_train,

        y_train,

        eval_set=[
            (
                X_test,
                y_test
            )
        ],

        verbose=True
    )

    # ========================================================
    # PREDICTIONS
    # ========================================================

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )

    # Default threshold

    predictions = (
        probabilities >= 0.50
    ).astype(int)

    # ========================================================
    # METRICS
    # ========================================================

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    print(
        f"\nROC-AUC:   {auc:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1:        {f1:.4f}"
    )

    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    print(
        "\nConfusion matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            predictions
        )
    )

    # ========================================================
    # CLASSIFICATION REPORT
    # ========================================================

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "NORMAL",
                "FRAUD"
            ],
            zero_division=0
        )
    )

    # ========================================================
    # THRESHOLD ANALYSIS
    # ========================================================

    print("\n" + "=" * 60)
    print("THRESHOLD ANALYSIS")
    print("=" * 60)

    thresholds = [
        0.10,
        0.20,
        0.30,
        0.40,
        0.50,
        0.60,
        0.70,
        0.80,
        0.90
    ]

    for threshold in thresholds:

        threshold_predictions = (
            probabilities >= threshold
        ).astype(int)

        p = precision_score(
            y_test,
            threshold_predictions,
            zero_division=0
        )

        r = recall_score(
            y_test,
            threshold_predictions,
            zero_division=0
        )

        f = f1_score(
            y_test,
            threshold_predictions,
            zero_division=0
        )

        detected = np.sum(
            threshold_predictions == 1
        )

        print(
            f"\nThreshold: {threshold:.2f}"
        )

        print(
            f"Detected:  {detected}"
        )

        print(
            f"Precision: {p:.4f}"
        )

        print(
            f"Recall:    {r:.4f}"
        )

        print(
            f"F1:        {f:.4f}"
        )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE")
    print("=" * 60)

    importance = pd.DataFrame({

        "feature": ML_FEATURES,

        "importance":
            model.feature_importances_

    }).sort_values(
        "importance",
        ascending=False
    )

    print(
        importance.to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    print("\n" + "=" * 60)
    print("SAVING MODEL")
    print("=" * 60)

    joblib.dump(
        model,
        MODEL_PATH
    )

    # ========================================================
    # SAVE FEATURE LIST
    # ========================================================

    with open(
        FEATURE_PATH,
        "w"
    ) as f:

        json.dump(
            ML_FEATURES,
            f,
            indent=4
        )

    print(
        "\nModel saved to:"
    )

    print(
        MODEL_PATH
    )

    print(
        "\nFeature list saved to:"
    )

    print(
        FEATURE_PATH
    )

    # ========================================================
    # FINAL SUCCESS
    # ========================================================

    print("\n" + "=" * 60)
    print("SUCCESS")
    print("=" * 60)

    print(
        "\nOne unified XGBoost model was trained using:"
    )

    print(
        "1. Benchmark normal transactions"
    )

    print(
        "2. Benchmark fraud transactions"
    )

    print(
        "3. Forge normal transactions"
    )

    print(
        "4. Forge-generated attack transactions"
    )

    print(
        "\nCommon features:"
    )

    for feature in ML_FEATURES:
        print(
            " -",
            feature
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()