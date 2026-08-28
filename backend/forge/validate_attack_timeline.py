import json
from collections import Counter


INPUT_FILE = "data/generated/attack_timeline.json"


def main():

    print("Loading attack timeline...")
    print("--------------------------------")

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    # ---------------------------------------
    # Extract timeline
    # ---------------------------------------

    if isinstance(data, dict):

        if "timeline" in data:

            timeline = data["timeline"]

        elif "accounts" in data:

            accounts = data["accounts"]

            if not accounts:
                raise ValueError(
                    "No accounts found."
                )

            timeline = accounts[0].get(
                "timeline",
                []
            )

        else:

            raise ValueError(
                "Unknown JSON structure."
            )

    elif isinstance(data, list):

        timeline = data

    else:

        raise ValueError(
            "Invalid JSON format."
        )

    if not isinstance(timeline, list):

        raise ValueError(
            "Timeline is not a list."
        )

    if not timeline:

        raise ValueError(
            "Timeline is empty."
        )

    # ---------------------------------------
    # Basic statistics
    # ---------------------------------------

    print("TOTAL:", len(timeline))

    phases = Counter(
        event.get("phase")
        for event in timeline
        if isinstance(event, dict)
    )

    print("PHASES:", phases)

    # ---------------------------------------
    # Days
    # ---------------------------------------

    days = [
        event.get("day")
        for event in timeline
        if isinstance(event, dict)
        and isinstance(event.get("day"), int)
    ]

    if days:

        print(
            "DAYS:",
            min(days),
            "-",
            max(days)
        )

    else:

        print(
            "DAYS: No valid days found"
        )

    # ---------------------------------------
    # Attack events
    # ---------------------------------------

    attack_events = [

        event
        for event in timeline

        if (
            isinstance(event, dict)
            and event.get("phase") == "ATTACK"
        )
    ]

    print(
        "ATTACK EVENTS:",
        len(attack_events)
    )

    # ---------------------------------------
    # Show attack samples
    # ---------------------------------------

    if attack_events:

        print("--------------------------------")

        print("FIRST ATTACK EVENT:")

        print(
            json.dumps(
                attack_events[0],
                indent=2
            )
        )

        print("--------------------------------")

        print("LAST ATTACK EVENT:")

        print(
            json.dumps(
                attack_events[-1],
                indent=2
            )
        )

    else:

        print("--------------------------------")
        print(
            "WARNING: No ATTACK events found."
        )

    print("--------------------------------")
    print("Validation completed.")


if __name__ == "__main__":
    main()