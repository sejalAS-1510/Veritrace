from backend.forge.sleeper_agent import (
    SleeperConfig,
    apply_sleeper_agent
)


def main():
    timeline = []

    # Create a small test timeline
    for day in range(1, 31):
        timeline.append({
            "step": day * 10,
            "day": day,
            "sequence": day,
            "phase": "NORMAL",
            "transaction": {
                "amount": 1000,
                "type": "PAYMENT",
                "nameOrig": "SYN-TEST",
                "nameDest": f"D-{day}"
            }
        })

    config = SleeperConfig(
        dormant_days=5,
        activation_days=2,
        attack_days=3,
        amount_multiplier=3.0
    )

    result = apply_sleeper_agent(
        timeline,
        normal_days=20,
        config=config
    )

    print("Sleeper Agent Test")
    print("--------------------------------")

    # Show generated phases
    for event in result:
        print(
            f"Day {event['day']:02d} | "
            f"{event['phase']:10s} | "
            f"Amount: "
            f"{event['transaction']['amount']}"
        )

    print("--------------------------------")
    print(
        f"Events generated: {len(result)}"
    )

    # ------------------------------------------------
    # VALIDATION 1: Normal behaviour
    # ------------------------------------------------

    normal_events = [
        event
        for event in result
        if event["phase"] == "NORMAL"
    ]

    assert len(normal_events) > 0

    for event in normal_events:
        assert event["transaction"]["amount"] == 1000

    print("Normal behaviour validation: PASSED")

    # ------------------------------------------------
    # VALIDATION 2: Attack behaviour
    # ------------------------------------------------

    attack_events = [
        event
        for event in result
        if event["phase"] == "ATTACK"
    ]

    assert len(attack_events) > 0

    for event in attack_events:
        assert event["transaction"]["amount"] > 1000

    print("Attack behaviour validation: PASSED")

    # ------------------------------------------------
    # VALIDATION 3: Phase transitions
    # ------------------------------------------------

    phases = [
        event["phase"]
        for event in result
    ]

    assert "NORMAL" in phases
    assert "DORMANT" in phases
    assert "ACTIVATION" in phases
    assert "ATTACK" in phases

    print("Phase transition validation: PASSED")

    # ------------------------------------------------
    # Final result
    # ------------------------------------------------

    print("--------------------------------")
    print("Sleeper Agent validation completed.")
    print("All tests passed.")


if __name__ == "__main__":
    main()