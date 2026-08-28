import json
from pathlib import Path

from backend.forge.generator import generate_account_history
from backend.forge.dataset_loader import load_paysim_data
from backend.forge.transaction_profile import build_paysim_profile

def generate_batch(number_of_accounts=500):

    print()
    print("=" * 60)
    print("FORGE - BATCH GENERATION")
    print("=" * 60)
    print()

    # ---------------------------------------
    # Load PaySim ONCE
    # ---------------------------------------

    print("Loading PaySim reference data...")

    paysim = load_paysim_data()

    print("Building transaction profile...")

    transaction_profile = build_paysim_profile(
        paysim
    )

    print("Reference profile ready.")
    print()

    # ---------------------------------------
    # Generate accounts
    # ---------------------------------------

    accounts = []

    print(
        f"Generating {number_of_accounts} accounts..."
    )
    print()

    for i in range(number_of_accounts):

        account = generate_account_history(
            number_of_transactions=200,
            transaction_profile=transaction_profile
        )

        accounts.append(account)

        if (i + 1) % 50 == 0:
            print(
                f"Generated: {i + 1}/{number_of_accounts}"
            )

    # ---------------------------------------
    # Save
    # ---------------------------------------

    output_file = Path(
        "data/generated/batch_dataset.json"
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            accounts,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("-" * 60)
    print("BATCH GENERATION COMPLETED")
    print("-" * 60)
    print(
        f"Accounts generated: {len(accounts)}"
    )
    print(
        f"Output: {output_file}"
    )
    print()

if __name__ == "__main__":
    generate_batch(500)