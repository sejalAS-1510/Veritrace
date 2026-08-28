from dataclasses import dataclass


@dataclass
class AttackScenario:
    name: str
    amount_multiplier: float
    new_destination_ratio: float
    transaction_frequency_multiplier: float
    description: str


SCENARIOS = {
    "LOW": AttackScenario(
        name="LOW",
        amount_multiplier=1.5,
        new_destination_ratio=0.3,
        transaction_frequency_multiplier=1.2,
        description="Subtle behavioural change"
    ),

    "MEDIUM": AttackScenario(
        name="MEDIUM",
        amount_multiplier=3.0,
        new_destination_ratio=0.6,
        transaction_frequency_multiplier=1.5,
        description="Moderate behavioural change"
    ),

    "HIGH": AttackScenario(
        name="HIGH",
        amount_multiplier=5.0,
        new_destination_ratio=0.9,
        transaction_frequency_multiplier=2.0,
        description="Strong behavioural change"
    )
}


def get_scenario(severity):
    if severity not in SCENARIOS:
        raise ValueError(
            f"Unknown severity: {severity}"
        )

    return SCENARIOS[severity]
