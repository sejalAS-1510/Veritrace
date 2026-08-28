import json

from backend.forge.timeline import build_account_timeline
from backend.forge.validate_timeline import validate_timeline

def load_transactions():
    with open(
        "data/generated/transactions.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def main():
    print("Loading generated transactions...")
    print("--------------------------------")

    transactions = load_transactions()

    print(f"Transactions loaded: {len(transactions)}")

    account_id = None

    if transactions:
        account_id = transactions[0].get("account_id")

    if not account_id:
        account_id = transactions[0].get("nameOrig")

    if not account_id:
        raise ValueError(
            "Could not find account_id or nameOrig in transactions."
        )

    account_transactions = [
        transaction
        for transaction in transactions
        if transaction.get("account_id") == account_id
        or transaction.get("nameOrig") == account_id
    ]

    result = build_account_timeline(
        account_id,
        account_transactions
    )
    validate_timeline(result["timeline"])

    print("Timeline validation : PASSED")

    print()
    print("Timeline created")
    print("--------------------------------")
    print(f"Account ID       : {result['account_id']}")
    print(f"Transactions     : {result['transaction_count']}")

    if result["timeline"]:
        first = result["timeline"][0]
        last = result["timeline"][-1]

        print(f"First step       : {first['step']}")
        print(f"Last step        : {last['step']}")

    print("--------------------------------")
    print("Real timeline test completed.")


if __name__ == "__main__":
    main()