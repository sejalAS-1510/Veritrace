from backend.forge.dataset_loader import load_paysim_data


def get_account_history(df, account_id):
    """
    Return all transactions belonging to one account.
    """

    account_history = df[
        df["nameOrig"] == account_id
    ].copy()

    account_history = account_history.sort_values(
        by="step"
    )

    return account_history


def show_account_history(df, account_id):
    history = get_account_history(df, account_id)

    print()
    print("=" * 50)
    print("          ACCOUNT HISTORY TEST")
    print("=" * 50)

    print()
    print("Account ID:", account_id)
    print("Transactions:", len(history))

    print()
    print("First transactions")
    print("-" * 50)

    columns = [
        "step",
        "type",
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "newbalanceOrig",
        "nameDest",
        "oldbalanceDest",
        "newbalanceDest",
    ]

    print(history[columns].head(10).to_string(index=False))

    print()
    print("=" * 50)


def main():
    print()
    print("Loading PaySim dataset...")

    df = load_paysim_data()

    print("Dataset loaded.")
    print("Total transactions:", len(df))

    # Pick one account from the dataset
    account_id = df["nameOrig"].iloc[0]

    show_account_history(df, account_id)


if __name__ == "__main__":
    main()