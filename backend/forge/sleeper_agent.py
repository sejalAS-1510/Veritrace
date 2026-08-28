import random
import uuid

from dataclasses import dataclass
from copy import deepcopy

from backend.forge.attack_scenarios import get_scenario


@dataclass
class SleeperConfig:
    dormant_days: int = 5
    activation_days: int = 2
    attack_days: int = 3
    amount_multiplier: float = 3.0
    new_destination_ratio: float = 0.7


@dataclass
class AttackConfig:
    attack_type: str = "SYNTHETIC_IDENTITY"
    severity: str = "MEDIUM"
    label: int = 1


@dataclass
class SleeperState:
    phase: str
    day: int
    activated: bool = False


def copy_transaction(transaction):
    return deepcopy(transaction)


def create_new_destination():
    return "D-" + uuid.uuid4().hex[:6].upper()


def modify_destination(transaction):
    updated = copy_transaction(transaction)

    updated["nameDest"] = create_new_destination()

    return updated


def modify_attack_amount(transaction, multiplier):
    updated = copy_transaction(transaction)

    amount = updated.get("amount", 0)

    if isinstance(amount, (int, float)) and amount > 0:
        updated["amount"] = round(
            amount * multiplier,
            2
        )

    return updated


def transform_attack_transaction(
    transaction,
    amount_multiplier,
    new_destination=True
):
    updated = copy_transaction(transaction)

    updated = modify_attack_amount(
        updated,
        amount_multiplier
    )

    if new_destination:
        updated = modify_destination(updated)

    return updated


def get_phase(day, normal_days, config):

    dormant_start = normal_days

    activation_start = (
        dormant_start +
        config.dormant_days
    )

    attack_start = (
        activation_start +
        config.activation_days
    )

    attack_end = (
        attack_start +
        config.attack_days
    )

    if day < dormant_start:
        return "NORMAL"

    if day < activation_start:
        return "DORMANT"

    if day < attack_start:
        return "ACTIVATION"

    if day < attack_end:
        return "ATTACK"

    return "POST_ATTACK"

def apply_sleeper_agent(
    timeline,
    normal_days,
    config=None,
    severity="MEDIUM"
):
    if config is None:
        config = SleeperConfig()

    scenario = get_scenario(severity)

    result = []

    for event in timeline:

        updated_event = dict(event)

        transaction = event.get(
            "transaction",
            {}
        )

        day = event.get(
            "day",
            transaction.get("day", 0)
        )

        phase = get_phase(
            day,
            normal_days,
            config
        )

        updated_event["phase"] = phase

        if phase == "ATTACK":

            use_new_destination = (
                random.random()
                < scenario.new_destination_ratio
            )

            transaction = transform_attack_transaction(
                transaction,
                scenario.amount_multiplier,
                use_new_destination
            )

            transaction["is_attack"] = True

            updated_event["attack_type"] = (
                "SYNTHETIC_IDENTITY"
            )

            updated_event["severity"] = severity

        else:

            transaction = copy_transaction(
                transaction
            )

            transaction["is_attack"] = False

            updated_event["attack_type"] = None
            updated_event["severity"] = None

        updated_event["transaction"] = transaction

        result.append(updated_event)

    return result


def inject_sleeper_attack(
    history,
    attack_start_step=721,
    number_of_attack_transactions=10
):

    if not history:
        return []

    attacked_history = []

    for transaction in history:
        attacked_history.append(
            transaction.copy()
        )

    account_id = history[0]["account_id"]

    current_balance = history[-1].get(
        "newbalanceOrig",
        0
    )

    for index in range(
        number_of_attack_transactions
    ):

        amount = random.randint(
            50000,
            200000
        )

        attack_transaction = {

            "account_id":
                account_id,

            "step":
                attack_start_step + index,

            "type":
                random.choice([
                    "TRANSFER",
                    "CASH_OUT"
                ]),

            "amount":
                amount,

            "nameOrig":
                account_id,

            "nameDest":
                "ATTACK-" +
                str(
                    random.randint(
                        10000,
                        99999
                    )
                ),

            "oldbalanceOrg":
                current_balance,

            "newbalanceOrig":
                max(
                    0,
                    current_balance - amount
                ),

            "oldbalanceDest":
                0,

            "newbalanceDest":
                amount,

            "is_attack":
                True
        }

        current_balance = (
            attack_transaction[
                "newbalanceOrig"
            ]
        )

        attacked_history.append(
            attack_transaction
        )

    return attacked_history