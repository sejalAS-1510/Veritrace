import json
from pathlib import Path


INPUT_FILE = "data/generated/batch_attack_timeline.json"
OUTPUT_FILE = "data/generated/ground_truth.json"


def load_attack_timeline():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def extract_accounts(data):

    if isinstance(data, dict):

        if "accounts" in data:
            return data["accounts"]

        if "timeline" in data:
            return [data]

    if isinstance(data, list):

        return data

    raise ValueError(
        "Unexpected attack timeline format"
    )


def create_ground_truth(accounts):

    dataset = []

    for account in accounts:

        account_id = account.get(
            "account_id"
        )

        timeline = account.get(
            "timeline",
            []
        )

        for event in timeline:

            transaction = event.get(
                "transaction",
                {}
            )

            phase = event.get(
                "phase",
                "NORMAL"
            )

            is_attack = bool(
                transaction.get(
                    "is_attack",
                    False
                )
            )

            label = 1 if (
                phase == "ATTACK"
                or is_attack
            ) else 0

            record = {

                "account_id":
                    account_id,

                "step":
                    event.get("step"),

                "day":
                    event.get("day"),

                "sequence":
                    event.get("sequence"),

                "amount":
                    transaction.get("amount"),

                "transaction_type":
                    transaction.get(
                        "transaction_type",
                        transaction.get("type")
                    ),

                "location":
                    transaction.get(
                        "location"
                    ),

                "device_id":
                    transaction.get(
                        "device_id"
                    ),

                "phase":
                    phase,

                "attack_type":
                    event.get(
                        "attack_type"
                    ),

                "severity":
                    event.get(
                        "severity"
                    ),

                "is_attack":
                    is_attack,

                "label":
                    label
            }

            dataset.append(record)

    return dataset


def save_dataset(dataset):

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
            dataset,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():

    print()
    print("=" * 60)
    print("FORGE - GROUND TRUTH DATASET")
    print("=" * 60)
    print()

    data = load_attack_timeline()

    accounts = extract_accounts(data)

    print(
        "Accounts:",
        len(accounts)
    )

    dataset = create_ground_truth(
        accounts
    )

    save_dataset(dataset)

    attack_count = sum(
        1
        for record in dataset
        if record["label"] == 1
    )

    normal_count = sum(
        1
        for record in dataset
        if record["label"] == 0
    )

    print()
    print("-" * 60)
    print("GROUND TRUTH CREATED")
    print("-" * 60)

    print(
        "Total records:",
        len(dataset)
    )

    print(
        "Normal records:",
        normal_count
    )

    print(
        "Attack records:",
        attack_count
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print()
    print("Ground-truth generation completed.")


if __name__ == "__main__":
    main()