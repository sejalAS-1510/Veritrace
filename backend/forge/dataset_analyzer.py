from backend.forge.dataset_loader import(
    load_training_data ,
    load_paysim_data
)

from backend.forge.config import REFERENCE_FIELDS


def validate_columns(df):
    missing = [
        field for field in REFERENCE_FIELDS
        if field not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required fields: {missing}"
        )

    return True


def show_basic_info(df):
    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    print("\nSelected fields:")
    for field in REFERENCE_FIELDS:
        print(" -", field)

def show_transaction_distribution(df):
    print("\nPayment channel distribution:")
    print(df["payment_channel"].value_counts(normalize=True))

def show_device_distribution(df):
    print("\nDevice distribution:")
    print(df["device_type"].value_counts(normalize=True))

def show_amount_statistics(df):
    print("\nTransaction amount statistics:")

    print(
        df["transaction_amount"].describe()
    )

def show_international_distribution(df):
    print("\nInternational transaction distribution:")
    print(
        df["is_international"].value_counts(normalize=True)
    )

def show_behavior_statistics(df):
    fields = [
        "txn_count_1h",
        "txn_count_24h",
        "failed_txn_count_24h",
        "geo_distance_from_last_txn",
        "amount_deviation_from_user_mean",
    ]

    print("\nBehavior statistics:")

    for field in fields:
        print(f"\n{field}")
        print(df[field].describe())

def analyze_paysim(df):
    print()
    print("=" * 50)
    print("PAYSIM ANALYSIS")
    print("=" * 50)

    print()
    print("Total transactions:", len(df))

    print()
    print("Transaction types:")

    print(df["type"].value_counts())

    print()
    print("Average transaction amount:")

    print(round(df["amount"].mean(), 2))

    print()
    print("Minimum transaction amount:")

    print(round(df["amount"].min(), 2))

    print()
    print("Maximum transaction amount:")

    print(round(df["amount"].max(), 2))

def analyze_training(df):

    print()
    print("=" * 50)
    print("TRAINING DATA ANALYSIS")
    print("=" * 50)

    print()
    print("Total records:", len(df))

    print()
    print("Columns:")

    print(df.columns.tolist())



def main():

    print()
    print("=" * 60)
    print("           VERITRACE DATASET ANALYZER")
    print("=" * 60)

    print()
    print("Loading datasets...")

    paysim = load_paysim_data()
    train = load_training_data()

    print("Datasets loaded successfully.")

    analyze_paysim(paysim)

    analyze_training(train)

    print()
    print("=" * 60)
    print("             ANALYSIS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()