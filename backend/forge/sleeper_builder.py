import json

from backend.forge.sleeper_agent import (
    SleeperConfig,
    apply_sleeper_agent
)


INPUT_FILE = "data/generated/timeline.json"
OUTPUT_FILE = "data/generated/attack_timeline.json"


def load_timeline():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_attack_timeline(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def process_account(account):

    if not isinstance(account, dict):
        return None

    timeline = account.get("timeline", [])

    if not isinstance(timeline, list) or not timeline:
        return None

    attack_timeline = apply_sleeper_agent(
        timeline,
        normal_days=100,
        config=SleeperConfig(
            dormant_days=20,
            activation_days=20,
            attack_days=20
        ),
        severity="MEDIUM"
    )

    updated_account = dict(account)

    updated_account["timeline"] = attack_timeline

    updated_account["transaction_count"] = len(
        attack_timeline
    )

    return updated_account


def main():

    print("Loading timeline...")
    print("--------------------------------")

    data = load_timeline()

    # ---------------------------------------------
    # FORMAT 1:
    # timeline.json is a list of accounts
    # ---------------------------------------------

    if isinstance(data, list):

        output_accounts = []

        for account in data:

            updated_account = process_account(account)

            if updated_account is not None:
                output_accounts.append(updated_account)

        result = {
            "accounts": output_accounts
        }

    # ---------------------------------------------
    # FORMAT 2:
    # timeline.json is a dictionary
    # ---------------------------------------------

    elif isinstance(data, dict):

        # Dictionary containing accounts
        if "accounts" in data:

            output_accounts = []

            for account in data["accounts"]:

                updated_account = process_account(account)

                if updated_account is not None:
                    output_accounts.append(updated_account)

            result = {
                "accounts": output_accounts
            }

        # Dictionary containing one timeline
        elif "timeline" in data:

            timeline = data["timeline"]

            attack_timeline = apply_sleeper_agent(
                timeline,
                normal_days=100,
                config=SleeperConfig(
                    dormant_days=20,
                    activation_days=20,
                    attack_days=20
                ),
                severity="MEDIUM"
            )

            result = {
                "timeline": attack_timeline
            }

        else:

            raise ValueError(
                "Unexpected timeline.json format. "
                "Expected 'accounts' or 'timeline'."
            )

    else:

        raise ValueError(
            "Unexpected timeline.json format."
        )

    save_attack_timeline(result)

    print("Sleeper Agent build completed.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()