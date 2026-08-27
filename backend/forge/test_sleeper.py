from backend.forge.dataset_loader import (
    load_paysim_data
)

from backend.forge.transaction_profile import (
    build_paysim_profile
)

from backend.forge.history_generator import (
    generate_history
)

from backend.forge.sleeper_agent import (
    inject_sleeper_attack
)


def main():

    print("Loading PaySim...")

    df = load_paysim_data()

    profile = build_paysim_profile(df)

    history = generate_history(

        account_id="SYN-SLEEPER01",

        starting_balance=250000,

        destination_balance=50000,

        transaction_types=
            profile.transaction_types,

        average_amount=
            profile.average_amount,

        min_amount=
            profile.min_amount,

        max_amount=
            profile.max_amount,

        number_of_transactions=200
    )

    print()
    print(
        "Normal transactions:",
        len(history)
    )

    attacked_history = (
        inject_sleeper_attack(
            history
        )
    )

    attack_count = sum(
        1
        for transaction
        in attacked_history
        if transaction.get(
            "is_attack",
            False
        )
    )

    print(
        "Total transactions after attack:",
        len(attacked_history)
    )

    print(
        "Attack transactions:",
        attack_count
    )

    print()
    print("LAST 10 TRANSACTIONS")
    print("-" * 60)

    for transaction in (
        attacked_history[-10:]
    ):

        print(transaction)


if __name__ == "__main__":
    main()