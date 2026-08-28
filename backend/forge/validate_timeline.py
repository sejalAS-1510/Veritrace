def validate_timeline(timeline):
    if not timeline:
        raise ValueError("Timeline is empty.")

    steps = [
        event["step"]
        for event in timeline
    ]

    if steps != sorted(steps):
        raise ValueError(
            "Timeline is not sorted chronologically."
        )

    for event in timeline:
        required_fields = [
            "step",
            "day",
            "sequence",
            "phase",
            "transaction"
        ]

        for field in required_fields:
            if field not in event:
                raise ValueError(
                    f"Missing timeline field: {field}"
                )

    return True