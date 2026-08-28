import json


def main():
    with open(
        "data/generated/timeline.json",
        "r",
        encoding="utf-8"
    ) as file:
        accounts = json.load(file)

    print("Account history check")
    print("--------------------------------")

    total_accounts = len(accounts)

    accounts_without_history = []

    for account in accounts:
        account_id = account.get("account_id")
        count = account.get("transaction_count", 0)

        print(
            f"{account_id} -> {count} transactions"
        )

        if count == 0:
            accounts_without_history.append(
                account_id
            )

    print("--------------------------------")
    print(f"Total accounts : {total_accounts}")
    print(
        f"Without history: "
        f"{len(accounts_without_history)}"
    )

    if accounts_without_history:
        raise ValueError(
            "Some accounts have no transaction history."
        )

    print("Account history validation: PASSED")


if __name__ == "__main__":
    main()