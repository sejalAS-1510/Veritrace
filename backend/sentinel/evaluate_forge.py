import os
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from forge_adapter import (
    load_forge_data,
    create_forge_features,
    ML_FEATURES
)


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models/xgboost_unified_fraud_model.pkl"
)

FORGE_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "generated",
    "batch_attack_timeline.json"
)


def extract_ground_truth(df):

    labels = []

    for value in df["transaction"]:

        if isinstance(value, dict):
            labels.append(
                int(value.get("is_attack", False))
            )

        else:
            labels.append(0)

    return np.array(labels)


def main():

    print("=" * 60)
    print("FORGE MODEL EVALUATION")
    print("=" * 60)

    # ---------------------------------------------------------
    # Load model
    # ---------------------------------------------------------

    print("\nLoading model...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded.")

    # ---------------------------------------------------------
    # Load Forge data
    # ---------------------------------------------------------

    print("\nLoading Forge data...")

    df = load_forge_data(
        FORGE_DATA_PATH
    )

    print(
        f"Forge rows: {len(df)}"
    )

    # ---------------------------------------------------------
    # Ground truth
    # ---------------------------------------------------------

    y_true = extract_ground_truth(df)

    print("\nActual Forge labels:")

    print(
        pd.Series(y_true)
        .value_counts()
        .sort_index()
    )

    # ---------------------------------------------------------
    # Create ML features
    # ---------------------------------------------------------

    print("\nCreating features...")

    X = create_forge_features(df)

    X = X[ML_FEATURES]

    # ---------------------------------------------------------
    # Predict probability
    # ---------------------------------------------------------

    print("\nRunning XGBoost...")

    y_probability = (
        model.predict_proba(X)[:, 1]
    )

    # ---------------------------------------------------------
    # Test several thresholds
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("THRESHOLD ANALYSIS")
    print("=" * 60)

    thresholds = [
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
    0.95,
    0.99
]

    for threshold in thresholds:

        y_pred = (
            y_probability >= threshold
        ).astype(int)

        precision = precision_score(
            y_true,
            y_pred,
            zero_division=0
        )

        recall = recall_score(
            y_true,
            y_pred,
            zero_division=0
        )

        f1 = f1_score(
            y_true,
            y_pred,
            zero_division=0
        )

        print(
            f"\nThreshold: {threshold:.2f}"
        )

        print(
            f"Detected: {y_pred.sum()} "
            f"/ {y_true.sum()} attacks"
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

    # ---------------------------------------------------------
    # ROC-AUC
    # ---------------------------------------------------------

    if len(np.unique(y_true)) == 2:

        auc = roc_auc_score(
            y_true,
            y_probability
        )

        print("\n" + "=" * 60)
        print(
            f"ROC-AUC: {auc:.4f}"
        )
        print("=" * 60)

    # ---------------------------------------------------------
    # Default threshold
    # ---------------------------------------------------------

    threshold = 0.50

    y_pred = (
        y_probability >= threshold
    ).astype(int)

    print("\n" + "=" * 60)
    print("CONFUSION MATRIX @ 0.50")
    print("=" * 60)

    print(
        confusion_matrix(
            y_true,
            y_pred
        )
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_true,
            y_pred,
            target_names=[
                "NORMAL",
                "FORGE_ATTACK"
            ],
            zero_division=0
        )
    )


if __name__ == "__main__":
    main()