import json

from backend.forge.timeline import build_account_timeline


def load_transactions():
    with open(
        "data/generated/transactions.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_timeline(data):
    with open(
        "data/generated/timeline.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():
    print("Building account timeline...")
    print("--------------------------------")

    transactions = load_transactions()

    accounts = {}

    for transaction in transactions:
        account_id = (
            transaction.get("account_id")
            or transaction.get("nameOrig")
        )

        if not account_id:
            continue

        accounts.setdefault(
            account_id,
            []
        ).append(transaction)

    timeline_data = []

    for account_id, account_transactions in accounts.items():
        account_timeline = build_account_timeline(
            account_id,
            account_transactions
        )

        timeline_data.append(
            account_timeline
        )

    save_timeline(timeline_data)

    print(f"Accounts processed : {len(timeline_data)}")
    print("Timeline saved     : data/generated/timeline.json")
    print("--------------------------------")
    print("Timeline build completed.")


if __name__ == "__main__":
    main()