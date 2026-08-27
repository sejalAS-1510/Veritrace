from backend.forge.dataset_loader import load_paysim_data
from backend.forge.transaction_profile import build_paysim_profile
from backend.forge.history_generator import generate_history


def main():

    print("Loading PaySim...")

    df = load_paysim_data()

    profile = build_paysim_profile(df)

    account_id = "SYN-TEST01"

    starting_balance = 100000

    destination_balance = 50000

    history = generate_history(
        account_id=account_id,
        starting_balance=starting_balance,
        destination_balance=destination_balance,
        transaction_types=profile.transaction_types,
        average_amount=profile.average_amount,
        min_amount=profile.min_amount,
        max_amount=profile.max_amount,
        number_of_transactions=20
    )

    print()
    print("=" * 60)
    print("GENERATED ACCOUNT HISTORY")
    print("=" * 60)

    for transaction in history[:10]:

        print(transaction)

    print()
    print("Total transactions:", len(history))

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()