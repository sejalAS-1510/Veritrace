"""
VeriTrace Sentinel — XGBoost Fraud Detection

Responsibilities:
1. Existing trajectory-based anomaly detection
2. Feature engineering for the Digital Payment Fraud Detection Benchmark
3. XGBoost fraud model training
4. Model evaluation
5. Model saving/loading

IMPORTANT:
- Forge data is NOT used for XGBoost training.
- XGBoost is trained on the benchmark dataset.
- Forge data will later be converted through forge_adapter.py
  and used as an unseen attack/test set.
"""

import os
import joblib
import numpy as np
import pandas as pd

from typing import Any, Dict, List

from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from xgboost import XGBClassifier


# ============================================================
# XGBOOST FEATURE LIST
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
# EXISTING TRAJECTORY FEATURE EXTRACTION
# ============================================================

def extract_features(
    timeline: List[Dict[str, Any]]
) -> Dict[str, float]:

    if not timeline or len(timeline) < 3:
        return {
            "spend_smoothness": 0.0,
            "spend_monotonicity": 0.0,
            "login_regularity": 0.0,
            "variance_score": 0.5,
            "bust_out_ratio": 0.0,
            "device_change_rate": 0.0,
        }

    # --------------------------------------------------------
    # Find fraud strike
    # --------------------------------------------------------

    strike_idx = None

    for i, t in enumerate(timeline):

        if t.get("fraud_strike", False):

            strike_idx = i
            break

    # --------------------------------------------------------
    # Incubation period
    # --------------------------------------------------------

    if strike_idx is not None and strike_idx >= 3:

        incubation = timeline[:strike_idx]

        final_spend = float(
            timeline[strike_idx].get(
                "spend",
                0.0
            )
        )

    else:

        incubation = timeline

        final_spend = 0.0

    # --------------------------------------------------------
    # Spend values
    # --------------------------------------------------------

    spends = np.array(
        [
            float(
                t.get(
                    "spend",
                    0.0
                )
            )
            for t in incubation
        ],
        dtype=np.float64
    )

    # --------------------------------------------------------
    # Login values
    # --------------------------------------------------------

    logins = np.array(
        [
            float(
                t.get(
                    "login_count",
                    0.0
                )
            )
            for t in incubation
        ],
        dtype=np.float64
    )

    n = len(spends)

    # --------------------------------------------------------
    # Spend monotonicity
    # --------------------------------------------------------

    diffs = np.diff(spends)

    spend_monotonicity = float(
        np.sum(diffs >= -0.01)
        /
        max(
            1,
            len(diffs)
        )
    )

    # --------------------------------------------------------
    # Spend smoothness
    # --------------------------------------------------------

    weeks_arr = np.arange(
        1,
        n + 1,
        dtype=np.float64
    )

    if (
        n >= 3
        and np.std(spends) > 1e-4
    ):

        coeffs = np.polyfit(
            weeks_arr,
            spends,
            1
        )

        fitted = np.polyval(
            coeffs,
            weeks_arr
        )

        ss_res = float(
            np.sum(
                (spends - fitted) ** 2
            )
        )

        ss_tot = float(
            np.sum(
                (
                    spends
                    - np.mean(spends)
                ) ** 2
            )
        )

        r2 = 1.0 - (
            ss_res
            /
            (
                ss_tot
                + 1e-8
            )
        )

        spend_smoothness = float(
            np.clip(
                r2,
                0.0,
                1.0
            )
        )

        if coeffs[0] <= 0:

            spend_smoothness *= 0.3

    else:

        spend_smoothness = 0.5

    # --------------------------------------------------------
    # Login regularity
    # --------------------------------------------------------

    login_std = float(
        np.std(logins)
    )

    login_regularity = float(
        1.0
        /
        (
            1.0
            +
            login_std
        )
    )

    # --------------------------------------------------------
    # Spending variance
    # --------------------------------------------------------

    mean_spend = float(
        np.mean(spends)
    )

    if mean_spend > 1e-4:

        variance_score = float(
            np.clip(
                np.std(spends)
                /
                mean_spend,
                0.0,
                1.0
            )
        )

    else:

        variance_score = 0.5

    # --------------------------------------------------------
    # Bust-out ratio
    # --------------------------------------------------------

    if (
        mean_spend > 1e-4
        and final_spend > 0
    ):

        raw_ratio = (
            final_spend
            /
            mean_spend
        )

        bust_out_ratio = float(
            np.clip(
                (
                    raw_ratio
                    - 1.0
                )
                /
                19.0,
                0.0,
                1.0
            )
        )

    else:

        bust_out_ratio = 0.0

    # --------------------------------------------------------
    # Device change rate
    # --------------------------------------------------------

    device_changes = sum(
        1
        for t in incubation
        if t.get(
            "new_device",
            False
        )
    )

    device_change_rate = float(
        device_changes
        /
        max(
            1,
            len(incubation)
        )
    )

    return {

        "spend_smoothness":
            round(
                spend_smoothness,
                4
            ),

        "spend_monotonicity":
            round(
                spend_monotonicity,
                4
            ),

        "login_regularity":
            round(
                login_regularity,
                4
            ),

        "variance_score":
            round(
                variance_score,
                4
            ),

        "bust_out_ratio":
            round(
                bust_out_ratio,
                4
            ),

        "device_change_rate":
            round(
                device_change_rate,
                4
            ),
    }


# ============================================================
# TRANSACTION ANOMALY SCORE
# ============================================================

def transaction_anomaly_score(
    timeline: List[Dict[str, Any]]
) -> float:

    if (
        not timeline
        or len(timeline) < 4
    ):

        return 0.0

    spends = [
        float(
            t.get(
                "spend",
                0.0
            )
        )
        for t in timeline
    ]

    final = spends[-1]

    history = np.array(
        spends[:-1],
        dtype=np.float64
    )

    if len(history) < 3:

        return 0.0

    mu = float(
        np.mean(history)
    )

    sigma = float(
        np.std(history)
    )

    max_hist = float(
        np.max(history)
    )

    effective_sigma = max(
        sigma,
        mu * 0.20,
        (
            max_hist
            - mu
        ) * 0.5
        + 1e-8
    )

    z = abs(
        final - mu
    ) / effective_sigma

    score = float(
        1.0
        -
        np.exp(
            -z / 6.0
        )
    )

    return round(
        float(
            np.clip(
                score,
                0.0,
                1.0
            )
        ),
        4
    )


# ============================================================
# EXISTING TRAJECTORY SCORER
# ============================================================

def score_trajectory(
    timeline: List[Dict[str, Any]],
    threshold: float = 0.55,
) -> Dict[str, Any]:

    if (
        not timeline
        or len(timeline) < 2
    ):

        empty_features = {

            "spend_smoothness":
                0.0,

            "spend_monotonicity":
                0.0,

            "login_regularity":
                0.0,

            "variance_score":
                0.5,

            "bust_out_ratio":
                0.0,

            "device_change_rate":
                0.0,
        }

        return {

            "risk_score":
                0.05,

            "flagged":
                False,

            "flag_week":
                None,

            "features":
                empty_features,

            "risk_breakdown": {

                "trajectory_risk":
                    0.05,

                "transaction_anomaly":
                    0.0,
            },
        }

    features = extract_features(
        timeline
    )

    tx_anomaly = (
        transaction_anomaly_score(
            timeline
        )
    )

    dcr = features[
        "device_change_rate"
    ]

    if dcr < 0.12:

        device_signal = float(
            1.0
            -
            min(
                1.0,
                abs(
                    dcr
                    - 0.06
                )
                /
                0.06
            )
        )

    else:

        device_signal = 0.5

    trajectory_risk = (

        0.30
        *
        features[
            "spend_smoothness"
        ]

        +

        0.25
        *
        features[
            "spend_monotonicity"
        ]

        +

        0.15
        *
        features[
            "login_regularity"
        ]

        +

        0.10
        *
        features[
            "bust_out_ratio"
        ]

        +

        0.10
        *
        (
            1.0
            -
            min(
                1.0,
                features[
                    "variance_score"
                ]
                * 1.5
            )
        )

        +

        0.10
        *
        device_signal
    )

    raw_score = (

        0.60
        *
        trajectory_risk

        +

        0.40
        *
        tx_anomaly
    )

    risk_score = round(

        float(
            np.clip(
                raw_score,
                0.02,
                0.99
            )
        ),

        3
    )

    flagged = bool(
        risk_score
        >=
        threshold
    )

    flag_week = None

    # --------------------------------------------------------
    # Find first point at which account becomes risky
    # --------------------------------------------------------

    if flagged:

        for w in range(
            4,
            len(timeline) + 1
        ):

            sub = timeline[:w]

            sub_feats = (
                extract_features(
                    sub
                )
            )

            sub_tx = (
                transaction_anomaly_score(
                    sub
                )
            )

            sub_dcr = (
                sub_feats[
                    "device_change_rate"
                ]
            )

            if sub_dcr < 0.12:

                sub_device = float(
                    1.0
                    -
                    min(
                        1.0,
                        abs(
                            sub_dcr
                            - 0.06
                        )
                        /
                        0.06
                    )
                )

            else:

                sub_device = 0.5

            sub_traj = (

                0.30
                *
                sub_feats[
                    "spend_smoothness"
                ]

                +

                0.25
                *
                sub_feats[
                    "spend_monotonicity"
                ]

                +

                0.15
                *
                sub_feats[
                    "login_regularity"
                ]

                +

                0.10
                *
                sub_feats[
                    "bust_out_ratio"
                ]

                +

                0.10
                *
                (
                    1.0
                    -
                    min(
                        1.0,
                        sub_feats[
                            "variance_score"
                        ]
                        * 1.5
                    )
                )

                +

                0.10
                *
                sub_device
            )

            sub_score = (

                0.60
                *
                sub_traj

                +

                0.40
                *
                sub_tx
            )

            if sub_score >= threshold:

                flag_week = w

                break

    return {

        "risk_score":
            risk_score,

        "flagged":
            flagged,

        "flag_week":
            flag_week,

        "features":
            features,

        "risk_breakdown": {

            "trajectory_risk":
                round(
                    trajectory_risk,
                    3
                ),

            "transaction_anomaly":
                round(
                    tx_anomaly,
                    3
                ),
        },
    }


# ============================================================
# BENCHMARK FEATURE ENGINEERING
# ============================================================

def create_benchmark_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    data = df.copy()

    # --------------------------------------------------------
    # Convert timestamp
    # --------------------------------------------------------

    data[
        "transaction_time"
    ] = pd.to_datetime(
        data[
            "transaction_time"
        ],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Sort by account and time
    # --------------------------------------------------------

    data = data.sort_values(
        [
            "customer_id",
            "transaction_time"
        ]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    data[
        "transaction_amount"
    ] = pd.to_numeric(
        data[
            "transaction_amount"
        ],
        errors="coerce"
    ).fillna(0.0)

    # --------------------------------------------------------
    # Account age
    # --------------------------------------------------------

    data[
        "account_age"
    ] = pd.to_numeric(
        data[
            "account_age_days"
        ],
        errors="coerce"
    ).fillna(0.0)

    # --------------------------------------------------------
    # Historical transaction count
    # --------------------------------------------------------

    data[
        "transaction_count"
    ] = (
        data.groupby(
            "customer_id"
        )
        .cumcount()
    )

    # --------------------------------------------------------
    # Historical transaction amount
    # --------------------------------------------------------

    previous_amount = (

        data.groupby(
            "customer_id"
        )[
            "transaction_amount"
        ]
        .shift(1)
    )

    data[
        "avg_transaction_amount"
    ] = (

        previous_amount
        .groupby(
            data[
                "customer_id"
            ]
        )
        .transform(
            "mean"
        )
    )

    data[
        "std_transaction_amount"
    ] = (

        previous_amount
        .groupby(
            data[
                "customer_id"
            ]
        )
        .transform(
            "std"
        )
    )

    data[
        "max_transaction_amount"
    ] = (

        previous_amount
        .groupby(
            data[
                "customer_id"
            ]
        )
        .transform(
            "max"
        )
    )

    # --------------------------------------------------------
    # Fill missing historical statistics
    # --------------------------------------------------------

    global_mean = float(
        data[
            "transaction_amount"
        ].mean()
    )

    data[
        "avg_transaction_amount"
    ] = data[
        "avg_transaction_amount"
    ].fillna(
        global_mean
    )

    data[
        "std_transaction_amount"
    ] = data[
        "std_transaction_amount"
    ].fillna(
        0.0
    )

    data[
        "max_transaction_amount"
    ] = data[
        "max_transaction_amount"
    ].fillna(
        global_mean
    )

    # --------------------------------------------------------
    # Time gaps
    # --------------------------------------------------------

    previous_time = (

        data.groupby(
            "customer_id"
        )[
            "transaction_time"
        ]
        .shift(1)
    )

    data[
        "time_gap"
    ] = (

        (
            data[
                "transaction_time"
            ]
            -
            previous_time
        )
        .dt.total_seconds()
        /
        3600.0
    )

    # --------------------------------------------------------
    # Average historical time gap
    # --------------------------------------------------------

    data[
        "avg_time_gap"
    ] = (

        data.groupby(
            "customer_id"
        )[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
    )

    # --------------------------------------------------------
    # Historical time-gap standard deviation
    # --------------------------------------------------------

    data[
        "std_time_gap"
    ] = (

        data.groupby(
            "customer_id"
        )[
            "time_gap"
        ]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .std()
        )
    )

    # --------------------------------------------------------
    # Fill missing time features
    # --------------------------------------------------------

    median_gap = data[
        "time_gap"
    ].median()

    if pd.isna(median_gap):

        median_gap = 0.0

    data[
        "avg_time_gap"
    ] = data[
        "avg_time_gap"
    ].fillna(
        median_gap
    )

    data[
        "std_time_gap"
    ] = data[
        "std_time_gap"
    ].fillna(
        0.0
    )

    # --------------------------------------------------------
    # Payment channel
    # --------------------------------------------------------

    payment_channel = (

        data[
            "payment_channel"
        ]
        .astype(str)
        .str.lower()
    )

    # --------------------------------------------------------
    # Transaction categories
    # --------------------------------------------------------

    data[
        "is_cash_out"
    ] = (

        payment_channel
        .str.contains(
            "cash|withdraw",
            regex=True
        )
        .astype(int)
    )

    data[
        "is_payment"
    ] = (

        payment_channel
        .str.contains(
            "payment",
            regex=False
        )
        .astype(int)
    )

    data[
        "is_transfer"
    ] = (

        payment_channel
        .str.contains(
            "transfer",
            regex=False
        )
        .astype(int)
    )

    data[
        "is_debit"
    ] = (

        payment_channel
        .str.contains(
            "debit",
            regex=False
        )
        .astype(int)
    )

    # --------------------------------------------------------
    # Historical transaction-type ratios
    # --------------------------------------------------------

    for source, target in [

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

    ]:

        data[target] = (

            data.groupby(
                "customer_id"
            )[source]

            .transform(
                lambda x:
                x.shift(1)
                .expanding()
                .mean()
            )

            .fillna(0.0)
        )

    # --------------------------------------------------------
    # Final numerical feature dataframe
    # --------------------------------------------------------

    result = data[
        ML_FEATURES
    ].copy()

    result = result.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )

    result = result.fillna(
        0.0
    )

    return result


# ============================================================
# TRAIN XGBOOST
# ============================================================

def train_xgboost(
    train_csv: str,
    test_csv: str,
    model_path: str
):

    print(
        "=" * 60
    )

    print(
        "Loading benchmark dataset..."
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    train_df = pd.read_csv(
        train_csv
    )

    test_df = pd.read_csv(
        test_csv
    )

    print(
        f"Train shape: {train_df.shape}"
    )

    print(
        f"Test shape: {test_df.shape}"
    )

    print(
        "\nTraining fraud distribution:"
    )

    print(
        train_df[
            "is_fraud"
        ].value_counts()
    )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    print(
        "\nCreating training features..."
    )

    X_train = (
        create_benchmark_features(
            train_df
        )
    )

    print(
        "Training features created."
    )

    print(
        "\nCreating test features..."
    )

    X_test = (
        create_benchmark_features(
            test_df
        )
    )

    print(
        "Test features created."
    )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    y_train = (
        train_df[
            "is_fraud"
        ]
        .astype(int)
    )

    y_test = (
        test_df[
            "is_fraud"
        ]
        .astype(int)
    )

    # --------------------------------------------------------
    # Class imbalance
    # --------------------------------------------------------

    negative = int(
        (y_train == 0).sum()
    )

    positive = int(
        (y_train == 1).sum()
    )

    scale_pos_weight = (

        negative
        /
        max(
            positive,
            1
        )
    )

    print(
        "\nClass statistics:"
    )

    print(
        f"Genuine: {negative}"
    )

    print(
        f"Fraud:   {positive}"
    )

    print(
        f"scale_pos_weight: "
        f"{scale_pos_weight:.2f}"
    )

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    model = XGBClassifier(

        n_estimators=300,

        learning_rate=0.05,

        max_depth=6,

        min_child_weight=3,

        subsample=0.8,

        colsample_bytree=0.8,

        scale_pos_weight=
            scale_pos_weight,

        objective=
            "binary:logistic",

        eval_metric=
            "aucpr",

        tree_method=
            "hist",

        random_state=42,

        n_jobs=-1,
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "Training XGBoost..."
    )

    print(
        "=" * 60
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

        verbose=False,
    )

    print(
        "XGBoost training complete."
    )

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    probabilities = (

        model.predict_proba(
            X_test
        )[:, 1]
    )

    threshold = 0.50

    predictions = (

        probabilities
        >= threshold
    ).astype(int)

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    pr_auc = (
        average_precision_score(
            y_test,
            probabilities
        )
    )

    roc_auc = (
        roc_auc_score(
            y_test,
            probabilities
        )
    )

    precision = (
        precision_score(
            y_test,
            predictions,
            zero_division=0
        )
    )

    recall = (
        recall_score(
            y_test,
            predictions,
            zero_division=0
        )
    )

    f1 = (
        f1_score(
            y_test,
            predictions,
            zero_division=0
        )
    )

    cm = (
        confusion_matrix(
            y_test,
            predictions
        )
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 60
    )

    print(
        "XGBOOST RESULTS"
    )

    print(
        "=" * 60
    )

    print(
        f"PR-AUC    : {pr_auc:.4f}"
    )

    print(
        f"ROC-AUC   : {roc_auc:.4f}"
    )

    print(
        f"Precision : {precision:.4f}"
    )

    print(
        f"Recall    : {recall:.4f}"
    )

    print(
        f"F1        : {f1:.4f}"
    )

    print(
        "\nConfusion Matrix:"
    )

    print(
        cm
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance = pd.DataFrame({

        "feature":
            ML_FEATURES,

        "importance":
            model.feature_importances_

    }).sort_values(
        "importance",
        ascending=False
    )

    print(
        "\nFeature Importance:"
    )

    print(
        importance.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(
            model_path
        )
        or ".",
        exist_ok=True
    )

    joblib.dump(
        model,
        model_path
    )

    # --------------------------------------------------------
    # Save feature names
    # --------------------------------------------------------

    feature_info_path = (
        model_path
        .replace(
            ".pkl",
            "_features.txt"
        )
    )

    with open(
        feature_info_path,
        "w"
    ) as f:

        for feature in ML_FEATURES:

            f.write(
                feature
                + "\n"
            )

    print(
        "\nModel saved to:"
    )

    print(
        model_path
    )

    print(
        "\nFeature list saved to:"
    )

    print(
        feature_info_path
    )

    return model


# ============================================================
# LOAD MODEL
# ============================================================

def load_xgboost_model(
    model_path=
        "models/xgboost_fraud_model.pkl"
):

    if not os.path.exists(
        model_path
    ):

        raise FileNotFoundError(
            f"Model not found: "
            f"{model_path}"
        )

    return joblib.load(
        model_path
    )


# ============================================================
# PREDICT FRAUD PROBABILITY
# ============================================================

def predict_fraud_probability(
    model,
    feature_row: pd.DataFrame
) -> float:

    probability = (

        model.predict_proba(
            feature_row[
                ML_FEATURES
            ]
        )[0][1]
    )

    return float(
        probability
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # These paths assume you run from:
    #
    # C:\Users\hruth\Desktop\Veritrace\backend\sentinel
    #
    # --------------------------------------------------------

    train_path = (
        "../data/transactions_train.csv"
    )

    test_path = (
        "../data/transactions_test.csv"
    )

    model_path = (
        "models/xgboost_fraud_model.pkl"
    )

    train_xgboost(

        train_csv=train_path,

        test_csv=test_path,

        model_path=model_path,
    )