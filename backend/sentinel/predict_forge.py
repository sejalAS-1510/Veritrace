import os
import json
import joblib
import pandas as pd
import numpy as np

from risk_engine import run_risk_engine


# ============================================================
# PATHS
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

BACKEND_DIR = os.path.dirname(
    CURRENT_DIR
)

DATA_DIR = os.path.join(
    BACKEND_DIR,
    "data"
)

GENERATED_DIR = os.path.join(
    DATA_DIR,
    "generated"
)

RESULTS_DIR = os.path.join(
    DATA_DIR,
    "results"
)

MODEL_DIR = os.path.join(
    CURRENT_DIR,
    "models"
)


# ============================================================
# FILE PATHS
# ============================================================

FORGE_FILE = os.path.join(
    GENERATED_DIR,
    "batch_attack_timeline.json"
)

TRANSACTION_RESULT_FILE = os.path.join(
    RESULTS_DIR,
    "forge_predictions.csv"
)

ACCOUNT_RESULT_FILE = os.path.join(
    RESULTS_DIR,
    "forge_account_risk.csv"
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
# DETECTION THRESHOLD
# ============================================================

# Based on your Forge evaluation:
#
# ROC-AUC = 0.9879
#
# At threshold 0.50:
# Recall    ~= 0.9985
# Precision ~= 0.386
#
# We use 0.50 for the initial demo.

DEFAULT_THRESHOLD = 0.50


# ============================================================
# FIND MODEL
# ============================================================

def find_model():

    if not os.path.exists(MODEL_DIR):

        raise FileNotFoundError(
            f"Model directory not found:\n{MODEL_DIR}"
        )

    files = os.listdir(MODEL_DIR)

    # Prefer joblib / pickle
    preferred_extensions = [
        ".pkl",
        ".joblib"
    ]

    for extension in preferred_extensions:

        candidates = [
            file
            for file in files
            if file.lower().endswith(extension)
        ]

        if candidates:

            # Prefer unified model if present
            unified = [
                file
                for file in candidates
                if "unified" in file.lower()
            ]

            selected = (
                unified[0]
                if unified
                else candidates[0]
            )

            path = os.path.join(
                MODEL_DIR,
                selected
            )

            print(
                f"Using model: {path}"
            )

            return path

    # XGBoost native JSON model
    json_candidates = [
        file
        for file in files
        if file.lower().endswith(".json")
    ]

    if json_candidates:

        unified = [
            file
            for file in json_candidates
            if "unified" in file.lower()
        ]

        selected = (
            unified[0]
            if unified
            else json_candidates[0]
        )

        path = os.path.join(
            MODEL_DIR,
            selected
        )

        print(
            f"Using XGBoost JSON model: {path}"
        )

        return path

    raise FileNotFoundError(
        "No trained XGBoost model found in:\n"
        f"{MODEL_DIR}\n\n"
        "Expected .pkl, .joblib or .json model."
    )


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    model_path = find_model()

    print()
    print("=" * 60)
    print("LOADING UNIFIED XGBOOST MODEL")
    print("=" * 60)

    # --------------------------------------------------------
    # Joblib / Pickle
    # --------------------------------------------------------

    if model_path.lower().endswith(
        (".pkl", ".joblib")
    ):

        model = joblib.load(
            model_path
        )

    # --------------------------------------------------------
    # XGBoost JSON
    # --------------------------------------------------------

    elif model_path.lower().endswith(".json"):

        try:

            from xgboost import XGBClassifier

            model = XGBClassifier()

            model.load_model(
                model_path
            )

        except Exception as e:

            raise RuntimeError(
                "Could not load XGBoost JSON model.\n"
                f"Error: {e}"
            )

    else:

        raise ValueError(
            f"Unsupported model format: {model_path}"
        )

    print("Model loaded successfully.")

    return model


# ============================================================
# VALIDATE FEATURES
# ============================================================

def prepare_features(features):

    if not isinstance(
        features,
        pd.DataFrame
    ):

        raise TypeError(
            "Forge adapter must return "
            "a pandas DataFrame."
        )

    # --------------------------------------------------------
    # Check missing columns
    # --------------------------------------------------------

    missing = [
        feature
        for feature in ML_FEATURES
        if feature not in features.columns
    ]

    if missing:

        raise ValueError(
            "Forge features are missing:\n"
            f"{missing}"
        )

    # --------------------------------------------------------
    # EXACT TRAINING FEATURE ORDER
    # --------------------------------------------------------

    features = features[
        ML_FEATURES
    ].copy()

    # --------------------------------------------------------
    # Convert everything to numeric
    # --------------------------------------------------------

    for column in ML_FEATURES:

        features[column] = pd.to_numeric(
            features[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Remove invalid values
    # --------------------------------------------------------

    features = features.replace(
        [np.inf, -np.inf],
        np.nan
    )

    features = features.fillna(
        0.0
    )

    return features


# ============================================================
# PREDICTION
# ============================================================

def predict(
    model,
    features,
    threshold=DEFAULT_THRESHOLD
):

    features = prepare_features(
        features
    )

    # --------------------------------------------------------
    # Check model feature count
    # --------------------------------------------------------

    if hasattr(model, "n_features_in_"):

        if model.n_features_in_ != len(
            ML_FEATURES
        ):

            raise ValueError(
                f"Model expects "
                f"{model.n_features_in_} features, "
                f"but Forge provides "
                f"{len(ML_FEATURES)} features."
            )

    # --------------------------------------------------------
    # Fraud probability
    # --------------------------------------------------------

    probabilities = model.predict_proba(
        features
    )

    if probabilities.shape[1] < 2:

        raise ValueError(
            "XGBoost model does not provide "
            "both normal and fraud probabilities."
        )

    # Class 1 = fraud
    risk_scores = probabilities[:, 1]

    risk_scores = np.asarray(
        risk_scores,
        dtype=float
    )

    risk_scores = np.clip(
        risk_scores,
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Binary prediction
    # --------------------------------------------------------

    predictions = (
        risk_scores >= threshold
    ).astype(int)

    # --------------------------------------------------------
    # Result dataframe
    # --------------------------------------------------------

    results = pd.DataFrame({

        "risk_score": risk_scores,

        "prediction": predictions,

        "prediction_label": np.where(
            predictions == 1,
            "FRAUD",
            "NORMAL"
        )
    })

    return results


# ============================================================
# ACCOUNT-LEVEL RISK
# ============================================================

def create_account_risk(
    transaction_results
):

    if "account_id" not in transaction_results.columns:

        raise ValueError(
            "transaction_results must contain "
            "'account_id'."
        )

    # --------------------------------------------------------
    # Aggregate transactions per account
    # --------------------------------------------------------

    account_risk = (

        transaction_results

        .groupby("account_id")

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
        ].clip(lower=1)
    )

    # --------------------------------------------------------
    # Account risk score
    #
    # Maximum transaction risk is given
    # the highest importance.
    # --------------------------------------------------------

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
    ] = (

        account_risk[
            "account_risk_score"
        ]

        .clip(
            0.0,
            1.0
        )
    )

    # --------------------------------------------------------
    # Account classification
    # --------------------------------------------------------

    account_risk[
        "account_prediction"
    ] = (

        account_risk[
            "account_risk_score"
        ]

        >= DEFAULT_THRESHOLD

    ).astype(int)

    account_risk[
        "account_prediction_label"
    ] = np.where(

        account_risk[
            "account_prediction"
        ] == 1,

        "SUSPICIOUS",

        "NORMAL"
    )

    return account_risk


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("VERITRACE SENTINEL")
    print("UNIFIED XGBOOST FRAUD DETECTION")
    print("=" * 60)

    # ========================================================
    # 1. CHECK FORGE FILE
    # ========================================================

    print()
    print("=" * 60)
    print("LOADING FORGE DATA")
    print("=" * 60)

    if not os.path.exists(FORGE_FILE):

        raise FileNotFoundError(
            f"Forge data not found:\n{FORGE_FILE}"
        )

    # ========================================================
    # 2. IMPORT FORGE ADAPTER
    # ========================================================

    try:

        from forge_adapter import (
            load_forge_data,
            create_forge_features
        )

    except ImportError as e:

        raise ImportError(
            "Could not import forge_adapter.py.\n"
            f"Error: {e}"
        )

    # ========================================================
    # 3. LOAD FORGE DATA
    # ========================================================

    forge_df = load_forge_data(
        FORGE_FILE
    )

    print(
        f"Forge rows: {len(forge_df)}"
    )

    print(
        "\nForge columns:"
    )

    print(
        forge_df.columns.tolist()
    )

    # ========================================================
    # 4. CREATE ML FEATURES
    # ========================================================

    print()
    print("=" * 60)
    print("CREATING FORGE FEATURES")
    print("=" * 60)

    features = create_forge_features(
        forge_df
    )

    features = prepare_features(
        features
    )

    print(
        f"Feature shape: {features.shape}"
    )

    print(
        "\nFeature order:"
    )

    print(
        features.columns.tolist()
    )

    # ========================================================
    # 5. VERIFY FEATURE COUNT
    # ========================================================

    if features.shape[1] != len(
        ML_FEATURES
    ):

        raise ValueError(
            f"Expected {len(ML_FEATURES)} "
            f"features but received "
            f"{features.shape[1]}."
        )

    # ========================================================
    # 6. LOAD UNIFIED MODEL
    # ========================================================

    model = load_model()

    # ========================================================
    # 7. RUN XGBOOST
    # ========================================================

    print()
    print("=" * 60)
    print("RUNNING UNIFIED XGBOOST")
    print("=" * 60)

    transaction_results = predict(
        model=model,
        features=features,
        threshold=DEFAULT_THRESHOLD
    )

    # ========================================================
    # 8. ATTACH ACCOUNT IDs
    # ========================================================

    if "account_id" not in forge_df.columns:

        raise ValueError(
            "Forge data does not contain "
            "'account_id'."
        )

    account_ids = (
        forge_df[
            "account_id"
        ]
        .reset_index(drop=True)
    )

    if len(account_ids) != len(
        transaction_results
    ):

        raise ValueError(
            "Number of Forge account IDs "
            "does not match number of predictions."
        )

    transaction_results[
        "account_id"
    ] = account_ids

    # ========================================================
    # 9. RUN RISK ENGINE
    # ========================================================

    print()
    print("=" * 60)
    print("RUNNING RISK ENGINE")
    print("=" * 60)

    try:

        risk_output = run_risk_engine(
            transaction_results
        )

        # risk_engine may return:
        # (transaction_results, account_risk)

        if isinstance(
            risk_output,
            tuple
        ):

            transaction_results = (
                risk_output[0]
            )

            print(
                "Risk engine executed successfully."
            )

        else:

            transaction_results = (
                risk_output
            )

            print(
                "Risk engine executed successfully."
            )

    except Exception as e:

        print(
            "\nWARNING:"
        )

        print(
            "Risk engine could not be executed."
        )

        print(
            f"Reason: {e}"
        )

        print(
            "Continuing with XGBoost results..."
        )

    # ========================================================
    # 10. ATTACH FORGE METADATA
    # ========================================================

    metadata_columns = [
        "step",
        "day",
        "sequence",
        "phase",
        "attack_type",
        "severity"
    ]

    for column in metadata_columns:

        if column in forge_df.columns:

            transaction_results[
                column
            ] = forge_df[
                column
            ].values

    # ========================================================
    # 11. ACCOUNT-LEVEL RISK
    # ========================================================

    print()
    print("=" * 60)
    print("CREATING ACCOUNT-LEVEL RISK")
    print("=" * 60)

    account_risk = create_account_risk(
        transaction_results
    )

    # ========================================================
    # 12. CREATE RESULT DIRECTORY
    # ========================================================

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True
    )

    # ========================================================
    # 13. SAVE TRANSACTION RESULTS
    # ========================================================

    transaction_results.to_csv(
        TRANSACTION_RESULT_FILE,
        index=False
    )

    # ========================================================
    # 14. SAVE ACCOUNT RESULTS
    # ========================================================

    account_risk.to_csv(
        ACCOUNT_RESULT_FILE,
        index=False
    )

    # ========================================================
    # 15. DISPLAY RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("PREDICTION RESULTS")
    print("=" * 60)

    print(
        "\nTransaction prediction distribution:"
    )

    print(
        transaction_results[
            "prediction_label"
        ].value_counts()
    )

    print(
        "\nRisk score statistics:"
    )

    print(
        transaction_results[
            "risk_score"
        ].describe()
    )

    print(
        "\nAccount risk distribution:"
    )

    print(
        account_risk[
            "account_prediction_label"
        ].value_counts()
    )

    # ========================================================
    # 16. FIRST TRANSACTIONS
    # ========================================================

    print()
    print("=" * 60)
    print("FIRST 20 TRANSACTION RESULTS")
    print("=" * 60)

    display_columns = [
        "account_id",
        "risk_score",
        "prediction",
        "prediction_label"
    ]

    for column in [
        "step",
        "phase",
        "attack_type"
    ]:

        if column in transaction_results.columns:

            display_columns.append(
                column
            )

    print(
        transaction_results[
            display_columns
        ]
        .head(20)
        .to_string(index=False)
    )

    # ========================================================
    # 17. FIRST ACCOUNTS
    # ========================================================

    print()
    print("=" * 60)
    print("FIRST 20 ACCOUNT RESULTS")
    print("=" * 60)

    print(
        account_risk
        .head(20)
        .to_string(index=False)
    )

    # ========================================================
    # 18. SAVED FILES
    # ========================================================

    print()
    print("=" * 60)
    print("FILES SAVED")
    print("=" * 60)

    print(
        f"\nTransaction predictions:\n"
        f"{TRANSACTION_RESULT_FILE}"
    )

    print(
        f"\nAccount risk:\n"
        f"{ACCOUNT_RESULT_FILE}"
    )

    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()