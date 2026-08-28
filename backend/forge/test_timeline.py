from backend.forge.timeline import (
    build_normal_timeline,
    get_phase_for_step,
    build_timeline,
    sort_timeline,
    timeline_to_dict
)


def main():

    phases = build_normal_timeline()

    print()
    print("=" * 60)
    print("              ACCOUNT TIMELINE TEST")
    print("=" * 60)

    for phase in phases:

        print()
        print(
            f"{phase.name}: "
            f"{phase.start_step} → "
            f"{phase.end_step}"
        )

    print()
    print("PHASE LOOKUP")
    print("-" * 40)

    test_steps = [
        50,
        200,
        600,
        710
    ]

    for step in test_steps:

        phase = get_phase_for_step(step)

        print(
            f"Step {step}: "
            f"{phase.name}"
        )
    transactions = [
        {
            "step": 30,
            "type": "PAYMENT",
            "amount": 500
        },
        {
            "step": 10,
            "type": "CASH_OUT",
            "amount": 1000
        },
        {
            "step": 20,
            "type": "TRANSFER",
            "amount": 750
        }
    ]
    timeline = build_timeline(transactions)

    timeline = sort_timeline(timeline)

    data = timeline_to_dict(timeline)

    print("Timeline test")
    print("------------------------")

    for event in data:
        print(
            f"Step: {event['step']} | "
            f"Day: {event['day']} | "
            f"Phase: {event['phase']} | "
            f"Type: {event['transaction']['type']}"
        )

    print("------------------------")
    print(f"Events created: {len(data)}")



if __name__ == "__main__":
    main()