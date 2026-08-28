import json
from pathlib import Path

from backend.forge.sleeper_agent import (
    SleeperConfig,
    apply_sleeper_agent
)


INPUT_FILE = "data/generated/batch_dataset.json"
OUTPUT_FILE = "data/generated/batch_attack_timeline.json"


def load_batch():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_batch(data):

    output_path = Path(
        OUTPUT_FILE
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def convert_account(account):

    profile = account["profile"]
    history = account["history"]

    timeline = []

    for index, transaction in enumerate(history):

        event = {
            "step": transaction.get(
                "step",
                index + 1
            ),

            "day": transaction.get(
                "step",
                index + 1
            ),

            "sequence": index + 1,

            "phase": "NORMAL",

            "transaction": transaction
        }

        timeline.append(event)

    attacked_timeline = apply_sleeper_agent(
        timeline,
        normal_days=100,
        config=SleeperConfig(
            dormant_days=20,
            activation_days=20,
            attack_days=20
        ),
        severity="MEDIUM"
    )

    return {
        "account_id": profile["account_id"],
        "profile": profile,
        "timeline": attacked_timeline
    }


def main():

    print()
    print("=" * 60)
    print("FORGE - BATCH ATTACK BUILDER")
    print("=" * 60)
    print()

    accounts = load_batch()

    print(
        "Input accounts:",
        len(accounts)
    )

    output_accounts = []

    for index, account in enumerate(accounts):

        result = convert_account(account)

        output_accounts.append(result)

        if (index + 1) % 50 == 0:
            print(
                f"Processed: {index + 1}/{len(accounts)}"
            )

    save_batch(output_accounts)

    print()
    print("-" * 60)
    print("BATCH ATTACK BUILD COMPLETED")
    print("-" * 60)

    print(
        "Accounts:",
        len(output_accounts)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()