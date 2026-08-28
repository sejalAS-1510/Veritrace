"""
VeriTrace — Forge ↔ Sentinel Adversarial Loop

Member 3: Adversarial Engine

Flow:

Forge generates timeline
        ↓
Sentinel scores timeline
        ↓
Detection feedback
        ↓
Mutation engine changes Forge parameters
        ↓
Next round
"""

import json
from pathlib import Path

from backend.forge.history_generator import (
    generate_timeline_adversarial
)

from backend.forge.mutation import (
    DEFAULT_PARAMS,
    mutate_params,
    params_to_generator_kwargs,
    describe_mutation
)

from backend.sentinel.trajectory_model import (
    score_trajectory
)


OUTPUT_FILE = Path(
    "data/generated/adversarial_rounds.json"
)


def run_adversarial_loop(
    rounds=5,
    account_id="ADV-TEST-001"
):
    """
    Run Forge ↔ Sentinel adversarial rounds.
    """

    current_params = DEFAULT_PARAMS.copy()

    results = []

    print()
    print("=" * 60)
    print("VERITRACE ADVERSARIAL LOOP")
    print("=" * 60)

    for round_number in range(1, rounds + 1):

        print()
        print(f"ROUND {round_number}")
        print("-" * 60)

        # ---------------------------------------------------------
        # 1. Forge generates timeline
        # ---------------------------------------------------------

        generator_kwargs = params_to_generator_kwargs(
            current_params
        )

        timeline = generate_timeline_adversarial(
            account_id=account_id,
            **generator_kwargs
        )

        print(
            "Events generated:",
            len(timeline)
        )

        # ---------------------------------------------------------
        # 2. Sentinel scores timeline
        # ---------------------------------------------------------

        score = score_trajectory(
            timeline
        )

        risk_score = score["risk_score"]
        flagged = score["flagged"]

        print(
            "Risk score:",
            risk_score
        )

        print(
            "Flagged:",
            flagged
        )

        print(
            "Features:",
            score["features"]
        )

        print(
            "Breakdown:",
            score["risk_breakdown"]
        )

        # ---------------------------------------------------------
        # 3. Extract detection feedback
        # ---------------------------------------------------------

        detection_features = score["features"].copy()

        # ---------------------------------------------------------
        # 4. Mutation
        # ---------------------------------------------------------

        next_params = mutate_params(
            current_params=current_params,
            detection_features=detection_features,
            was_detected=flagged,
            round_number=round_number
        )

        mutation_description = describe_mutation(
            current_params,
            next_params
        )

        print(
            "Mutation:",
            mutation_description
        )

        # ---------------------------------------------------------
        # 5. Save round
        # ---------------------------------------------------------

        results.append(
            {
                "round": round_number,
                "account_id": account_id,
                "risk_score": risk_score,
                "flagged": flagged,
                "features": score["features"],
                "risk_breakdown": score[
                    "risk_breakdown"
                ],
                "parameters_before": current_params.copy(),
                "parameters_after": next_params.copy(),
                "mutation": mutation_description,
                "event_count": len(timeline)
            }
        )

        # ---------------------------------------------------------
        # 6. Prepare next round
        # ---------------------------------------------------------

        current_params = next_params

    # -------------------------------------------------------------
    # Save complete adversarial experiment
    # -------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w"
    ) as f:

        json.dump(
            results,
            f,
            indent=4
        )

    print()
    print("=" * 60)
    print("ADVERSARIAL LOOP COMPLETED")
    print("=" * 60)

    print(
        "Rounds:",
        rounds
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    return results


if __name__ == "__main__":

    run_adversarial_loop(
        rounds=5
    )