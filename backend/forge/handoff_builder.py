import json
from pathlib import Path


INPUT_FILE = "data/generated/batch_attack_timeline.json"
OUTPUT_FILE = "data/handoff/sentinel_input.json"


def load_data():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def build_handoff(data):

    if isinstance(data, dict):
        accounts = data.get("accounts", [])
    elif isinstance(data, list):
        accounts = data
    else:
        raise ValueError("Invalid batch attack timeline format")

    handoff = []

    for account in accounts:

        if not isinstance(account, dict):
            continue

        account_id = account.get("account_id")

        timeline = account.get("timeline", [])

        if not account_id or not isinstance(timeline, list):
            continue

        events = []

        for event in timeline:

            if not isinstance(event, dict):
                continue

            transaction = event.get("transaction", {})

            events.append({
                "step": event.get("step"),
                "day": event.get("day"),
                "sequence": event.get("sequence"),
                "phase": event.get("phase"),
                "transaction": transaction,
                "attack_type": event.get("attack_type"),
                "severity": event.get("severity"),
                "is_attack": transaction.get("is_attack", False)
            })

        handoff.append({
            "account_id": account_id,
            "timeline": events
        })

    return {
        "dataset": "SENTINEL_FORGE_HANDOFF",
        "version": "1.0",
        "accounts": handoff
    }


def save_data(data):

    output_path = Path(OUTPUT_FILE)

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


def main():

    print("Building Forge → Sentinel handoff...")
    print("--------------------------------")

    data = load_data()

    result = build_handoff(data)

    save_data(result)

    print(
        "Accounts:",
        len(result["accounts"])
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print("--------------------------------")
    print("Handoff build completed.")


if __name__ == "__main__":
    main()