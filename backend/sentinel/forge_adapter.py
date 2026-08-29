import json
import ast
import re

import pandas as pd
import numpy as np


# ============================================================
# THESE MUST MATCH THE FEATURES USED BY XGBOOST
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
# LOAD FORGE JSON
# ============================================================

def load_forge_data(path):
    """
    Forge JSON structure:

    [
        {
            "account_id": "...",
            "profile": {...},
            "timeline": [
                {
                    "step": ...,
                    "day": ...,
                    "sequence": ...,
                    "phase": ...,
                    "transaction": ...,
                    "attack_type": ...,
                    "severity": ...
                }
            ]
        }
    ]

    Converts nested account timelines into
    a flat transaction dataframe.
    """

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list):
        raise ValueError(
            "Expected Forge JSON to contain a list of accounts."
        )

    rows = []

    for account in raw_data:

        account_id = account.get("account_id")

        timeline = account.get("timeline", [])

        if not isinstance(timeline, list):
            continue

        for event in timeline:

            if not isinstance(event, dict):
                continue

            row = event.copy()

            row["account_id"] = account_id

            rows.append(row)

    if not rows:
        raise ValueError(
            "No timeline transactions found in Forge JSON."
        )

    return pd.DataFrame(rows)


# ============================================================
# TRANSACTION PARSER
# ============================================================

def parse_transaction(value):
    """
    Try to extract useful information from Forge's
    'transaction' field.

    Supports:

    1. dictionary
    2. JSON string
    3. Python-dict-like string
    4. numeric value
    5. ordinary text

    Returns:

        amount
        transaction_type
    """

    amount = np.nan
    transaction_type = ""

    # --------------------------------------------------------
    # Case 1: dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        for key in [
            "amount",
            "transaction_amount",
            "value",
            "spend",
        ]:

            if key in value:

                try:
                    amount = float(
                        value[key]
                    )
                    break

                except (
                    ValueError,
                    TypeError
                ):
                    pass

        for key in [
            "type",
            "transaction_type",
            "payment_type",
        ]:

            if key in value:

                transaction_type = str(
                    value[key]
                )

                break

        return amount, transaction_type

    # --------------------------------------------------------
    # Case 2: missing value
    # --------------------------------------------------------

    if value is None:

        return amount, transaction_type

    text = str(value).strip()

    # --------------------------------------------------------
    # Case 3: JSON / Python dictionary stored as text
    # --------------------------------------------------------

    if (
        text.startswith("{")
        and text.endswith("}")
    ):

        parsed = None

        try:
            parsed = json.loads(text)

        except Exception:
            try:
                parsed = ast.literal_eval(text)

            except Exception:
                parsed = None

        if isinstance(parsed, dict):

            return parse_transaction(parsed)

    # --------------------------------------------------------
    # Case 4: direct numeric value
    # --------------------------------------------------------

    try:

        amount = float(text)

        return amount, transaction_type

    except ValueError:
        pass

    # --------------------------------------------------------
    # Case 5: try to find amount in text
    #
    # Examples:
    #
    # "payment of 500"
    # "amount=500"
    # "transaction: 1200"
    # --------------------------------------------------------

    amount_patterns = [

        r"amount\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",

        r"transaction_amount\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",

        r"value\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",

        r"spend\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",

        r"([0-9]+(?:\.[0-9]+)?)",
    ]

    for pattern in amount_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                amount = float(
                    match.group(1)
                )

                break

            except ValueError:
                pass

    # --------------------------------------------------------
    # Try to identify transaction type
    # --------------------------------------------------------

    upper_text = text.upper()

    if "CASH_OUT" in upper_text:
        transaction_type = "CASH_OUT"

    elif "CASH OUT" in upper_text:
        transaction_type = "CASH_OUT"

    elif "TRANSFER" in upper_text:
        transaction_type = "TRANSFER"

    elif "PAYMENT" in upper_text:
        transaction_type = "PAYMENT"

    elif "DEBIT" in upper_text:
        transaction_type = "DEBIT"

    elif "CASH_IN" in upper_text:
        transaction_type = "CASH_IN"

    elif "CASH IN" in upper_text:
        transaction_type = "CASH_IN"

    return amount, transaction_type


# ============================================================
# CREATE FEATURES
# ============================================================

def create_forge_features(df):

    data = df.copy()

    print(
        "\nRaw Forge columns:"
    )

    print(
        data.columns.tolist()
    )

    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    required_columns = [
        "account_id",
        "step",
        "transaction",
    ]

    for column in required_columns:

        if column not in data.columns:

            raise ValueError(
                f"Forge data is missing required column: "
                f"{column}"
            )

    # ========================================================
    # STEP
    # ========================================================

    data["step"] = pd.to_numeric(
        data["step"],
        errors="coerce"
    ).fillna(0.0)

    # ========================================================
    # PARSE TRANSACTION
    # ========================================================

    parsed = data[
        "transaction"
    ].apply(
        parse_transaction
    )

    data[
        "transaction_amount"
    ] = parsed.apply(
        lambda x: x[0]
    )

    data[
        "parsed_transaction_type"
    ] = parsed.apply(
        lambda x: x[1]
    )

    # ========================================================
    # IF FORGE TRANSACTION DOES NOT CONTAIN AMOUNT
    #
    # Use severity as a fallback signal rather than crashing.
    # ========================================================

    data[
        "transaction_amount"
    ] = pd.to_numeric(
        data["transaction_amount"],
        errors="coerce"
    )

    # If no amount exists, use 0.
    data[
        "transaction_amount"
    ] = data[
        "transaction_amount"
    ].fillna(0.0)

    # ========================================================
    # SORT BY ACCOUNT + TIME
    # ========================================================

    data = data.sort_values(
        [
            "account_id",
            "step"
        ]
    ).reset_index(
        drop=True
    )

    # ========================================================
    # ACCOUNT AGE
    # ========================================================

    account_min_step = (
        data.groupby(
            "account_id"
        )["step"]
        .transform("min")
    )

    account_max_step = (
        data.groupby(
            "account_id"
        )["step"]
        .transform("max")
    )

    data[
        "account_age"
    ] = (
        account_max_step
        -
        account_min_step
    )

    # ========================================================
    # TRANSACTION COUNT
    #
    # Historical transaction count.
    # Current transaction excluded.
    # ========================================================

    data[
        "transaction_count"
    ] = (
        data.groupby(
            "account_id"
        ).cumcount()
    )

    # ========================================================
    # HISTORICAL AMOUNT
    # ========================================================

    previous_amount = (
        data.groupby(
            "account_id"
        )[
            "transaction_amount"
        ]
        .shift(1)
    )

    previous_amount_grouped = (
        previous_amount.groupby(
            data["account_id"]
        )
    )

    data[
        "avg_transaction_amount"
    ] = (
        previous_amount_grouped
        .transform("mean")
    )

    data[
        "std_transaction_amount"
    ] = (
        previous_amount_grouped
        .transform("std")
    )

    data[
        "max_transaction_amount"
    ] = (
        previous_amount_grouped
        .transform("max")
    )

    # ========================================================
    # FALLBACKS
    # ========================================================

    global_mean = data[
        "transaction_amount"
    ].mean()

    if pd.isna(global_mean):
        global_mean = 0.0

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

    # ========================================================
    # TIME GAP
    # ========================================================

    previous_step = (
        data.groupby(
            "account_id"
        )[
            "step"
        ].shift(1)
    )

    data[
        "time_gap"
    ] = (
        data["step"]
        -
        previous_step
    )

    # ========================================================
    # HISTORICAL AVG TIME GAP
    # ========================================================

    data[
        "avg_time_gap"
    ] = (

        data.groupby(
            "account_id"
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

    # ========================================================
    # HISTORICAL STD TIME GAP
    # ========================================================

    data[
        "std_time_gap"
    ] = (

        data.groupby(
            "account_id"
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

    # ========================================================
    # TRANSACTION TYPE
    # ========================================================

    transaction_type = (
        data[
            "parsed_transaction_type"
        ]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # If parsed transaction type is empty,
    # try attack/transaction text.
    if "attack_type" in data.columns:

        fallback_text = (
            data["attack_type"]
            .astype(str)
            .str.upper()
        )

        transaction_type = (
            transaction_type
            .where(
                transaction_type
                != "",
                fallback_text
            )
        )

    # ========================================================
    # TYPE FLAGS
    # ========================================================

    data[
        "is_cash_out"
    ] = (
        transaction_type
        .str.contains(
            "CASH[_ ]?OUT",
            regex=True,
            na=False
        )
        .astype(int)
    )

    data[
        "is_payment"
    ] = (
        transaction_type
        .str.contains(
            "PAYMENT",
            regex=True,
            na=False
        )
        .astype(int)
    )

    data[
        "is_transfer"
    ] = (
        transaction_type
        .str.contains(
            "TRANSFER",
            regex=True,
            na=False
        )
        .astype(int)
    )

    data[
        "is_debit"
    ] = (
        transaction_type
        .str.contains(
            "DEBIT",
            regex=True,
            na=False
        )
        .astype(int)
    )

    # ========================================================
    # HISTORICAL TRANSACTION TYPE RATIOS
    # ========================================================

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
                "account_id"
            )[source]

            .transform(
                lambda x:
                x.shift(1)
                .expanding()
                .mean()
            )

            .fillna(0.0)
        )

    # ========================================================
    # FINAL FEATURE DATAFRAME
    # ========================================================

    features = data[
        ML_FEATURES
    ].copy()

    # ========================================================
    # CLEAN NUMERIC VALUES
    # ========================================================

    features = features.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )

    for column in ML_FEATURES:

        features[column] = pd.to_numeric(
            features[column],
            errors="coerce"
        )

    features = features.fillna(
        0.0
    )

    return features


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    path = (
        "../data/generated/"
        "batch_attack_timeline.json"
    )

    print(
        "=" * 60
    )

    print(
        "Loading Forge data..."
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    df = load_forge_data(
        path
    )

    print(
        "\nFlattened Forge data shape:"
    )

    print(
        df.shape
    )

    print(
        "\nFlattened Forge columns:"
    )

    print(
        df.columns.tolist()
    )

    # --------------------------------------------------------
    # SHOW ACTUAL DATA
    # --------------------------------------------------------

    print(
        "\nFirst 5 Forge transactions:"
    )

    print(
        df.head()
        .to_string()
    )

    print(
        "\nTransaction examples:"
    )

    print(
        df[
            "transaction"
        ]
        .head(10)
        .tolist()
    )

    if "attack_type" in df.columns:

        print(
            "\nAttack types:"
        )

        print(
            df[
                "attack_type"
            ]
            .value_counts()
            .head(20)
        )

    if "phase" in df.columns:

        print(
            "\nPhases:"
        )

        print(
            df[
                "phase"
            ]
            .value_counts()
        )

    if "severity" in df.columns:

        print(
            "\nSeverity:"
        )

        print(
            df[
                "severity"
            ]
            .value_counts()
        )

    # --------------------------------------------------------
    # CREATE FEATURES
    # --------------------------------------------------------

    features = create_forge_features(
        df
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "FORGE FEATURES"
    )

    print(
        "=" * 60
    )

    print(
        "\nFeature shape:"
    )

    print(
        features.shape
    )

    print(
        "\nFeature columns:"
    )

    print(
        features.columns.tolist()
    )

    print(
        "\nFirst 5 feature rows:"
    )

    print(
        features.head()
        .to_string()
    )

    print(
        "\nFeature data types:"
    )

    print(
        features.dtypes
    )

    print(
        "\nFeature statistics:"
    )

    print(
        features.describe()
        .to_string()
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    print(
        "\nChecking for NaN..."
    )

    print(
        features.isna().sum()
    )

    print(
        "\nChecking for infinity..."
    )

    print(
        np.isinf(
            features.to_numpy()
        ).sum()
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 60
    )

    print(
        "SUCCESS"
    )

    print(
        "=" * 60
    )

    print(
        "Forge data was successfully converted "
        "into XGBoost-compatible features."
    )