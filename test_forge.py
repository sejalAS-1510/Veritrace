import json

from backend.forge.generator import create_account
from backend.forge.timeline import (
    create_timeline,
    create_credit_utilization,
)


def main():

    print("======================================")
    print("        SENTINEL - FORGE")
    print("        DAY 2 TEST")
    print("======================================\n")

    # Create synthetic account
    account = create_account()

    print("Account created")
    print(f"ID     : {account['account_id']}")
    print(f"Name   : {account['name']}")
    print(f"City   : {account['city']}")
    print(f"Income : ₹{account['income']}")
    print()

    # Generate 180-day behavioral timeline
    timeline = create_timeline(account)

    print("Behavioral timeline created")
    print(f"Total events: {len(timeline)}")
    print()

    # Generate credit utilization history
    credit_history = create_credit_utilization(account)

    print("Credit utilization history")
    print("--------------------------")

    for record in credit_history:
        print(
            f"Month {record['month']}: "
            f"{record['utilization_percent']}%"
        )

    print()

    # Count different types of events
    event_counts = {}

    for event in timeline:

        event_type = event["event_type"]

        if event_type not in event_counts:
            event_counts[event_type] = 0

        event_counts[event_type] += 1

    print("Event summary")
    print("-------------")

    for event_type, count in event_counts.items():
        print(f"{event_type}: {count}")

    print()

    # Save timeline
    with open(
        "data/generated/timeline.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            timeline,
            file,
            indent=4
        )

    # Save credit history
    with open(
        "data/generated/credit_history.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            credit_history,
            file,
            indent=4
        )

    print("--------------------------------------")
    print("DAY 2 FORGE TEST PASSED")
    print("--------------------------------------")


if __name__ == "__main__":
    main()