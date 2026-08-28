import random


def generate_transaction(
    account_id,
    step,
    balance,
    destination_balance,
    transaction_types,
    average_amount,
    min_amount,
    max_amount
):

    transaction_type = random.choices(
    transaction_types,
    k=1
    )[0]

    destination_id = (
    "D-" +
    str(random.randint(10000, 99999))
) 
    # Generate an amount around the learned average.
    amount = random.gauss(
        average_amount,
        average_amount * 0.40
    )

    amount = max(
        min_amount,
        amount
    )

    amount = min(
        amount,
        max_amount
    )

    amount = min(
        amount,
        balance
    )

    amount = round(
        amount,
        2
    )

    if transaction_type == "CASH_IN":

     new_balance = balance + amount
 
    else:

     new_balance = balance - amount

    if new_balance < 0:

     amount = round(
        balance * 0.5,
        2
    )

    new_balance = balance - amount

    new_destination_balance = (
    destination_balance + amount
)

    transaction = {
        "account_id": account_id,
        "step": step,
        "type": transaction_type,
        "amount": amount,
        "nameOrig": account_id,
        "nameDest": destination_id,
        "oldbalanceOrg": round(balance, 2),
        "newbalanceOrig": round(new_balance, 2),
        "oldbalanceDest": round(
        destination_balance,
        2
        
    ),
    "newbalanceDest": round(
        new_destination_balance,
        2
    ),
     "is_attack": False
    }

    return transaction, new_balance, new_destination_balance


def generate_history(
    account_id,
    starting_balance,
    destination_balance,
    transaction_types,
    average_amount,
    min_amount,
    max_amount,
    number_of_transactions=200
):

    history = []

    balance = starting_balance

    destination_balance = random.randint(
        10000,
        100000
    )

    step = 1

    for _ in range(number_of_transactions):

        transaction, balance, destination_balance = generate_transaction(
            account_id=account_id,
            step=step,
            balance=balance,
            destination_balance=destination_balance,
            transaction_types=transaction_types,
            average_amount=average_amount,
            min_amount=min_amount,
            max_amount=max_amount
        )

        # IMPORTANT:
        # append INSIDE the loop
        history.append(transaction)

        step += random.randint(
            1,
            5
        )

    return history

def generate_timeline_adversarial(
    account_id,
    starting_balance=50000,
    destination_balance=50000,
    transaction_types=None,
    average_amount=2000,
    min_amount=100,
    max_amount=10000,
    number_of_transactions=200,
    noise_factor=0.035,
    dip_probability=0.04,
    dip_magnitude=0.15,
    login_jitter=1,
    ramp_rate_variance=0.05,
    strike_week_offset=0,
    base_spend_offset=0.0,
    surge_multiplier_cap=20.0,
):
    """
    Generate a Forge timeline using adversarial parameters.

    These parameters are supplied by mutation.py so Forge can
    change its behavioural pattern between adversarial rounds.
    """

    if transaction_types is None:
        transaction_types = [
            "PAYMENT",
            "TRANSFER",
            "DEBIT",
            "CASH_OUT"
        ]

    timeline = []

    balance = float(starting_balance)
    destination_balance = float(destination_balance)

    # Base behavioural spending level
    base_spend = max(
        float(min_amount),
        float(average_amount) + float(base_spend_offset)
    )

    for step in range(1, number_of_transactions + 1):

        # ---------------------------------------------------------
        # Behavioural spend
        # ---------------------------------------------------------

        noise = random.gauss(
            0,
            max(1.0, base_spend * noise_factor)
        )

        spend = base_spend + noise

        # Human-like spending dip
        if random.random() < dip_probability:
            spend *= (1.0 - dip_magnitude)

        # Keep amount valid
        spend = max(float(min_amount), spend)
        spend = min(float(max_amount), spend)
        spend = min(spend, max(balance, 0.0))

        spend = round(spend, 2)

        # ---------------------------------------------------------
        # Login behaviour
        # ---------------------------------------------------------

        login_base = 3

        jitter = random.randint(
            -int(login_jitter),
            int(login_jitter)
        )

        login_count = max(
            0,
            login_base + jitter
        )

        # ---------------------------------------------------------
        # Device behaviour
        # ---------------------------------------------------------

        new_device = random.random() < 0.02

        # ---------------------------------------------------------
        # Transaction
        # ---------------------------------------------------------

        transaction_type = random.choice(
            transaction_types
        )

        destination_id = (
            "D-" +
            str(random.randint(10000, 99999))
        )

        old_balance = balance

        if transaction_type == "CASH_IN":
            new_balance = balance + spend
        else:
            new_balance = max(
                0.0,
                balance - spend
            )

        new_destination_balance = (
            destination_balance + spend
        )

        transaction = {
            "account_id": account_id,
            "step": step,
            "type": transaction_type,
            "amount": spend,
            "nameOrig": account_id,
            "nameDest": destination_id,
            "oldbalanceOrg": round(old_balance, 2),
            "newbalanceOrig": round(new_balance, 2),
            "oldbalanceDest": round(
                destination_balance,
                2
            ),
            "newbalanceDest": round(
                new_destination_balance,
                2
            ),
            "is_attack": False
        }

        event = {
            "step": step,
            "day": step,
            "sequence": step,
            "phase": "NORMAL",

            "spend": spend,
            "login_count": login_count,
            "new_device": new_device,

            "transaction": transaction,

            "fraud_strike": False,
            "attack_type": None
        }

        timeline.append(event)

        balance = new_balance
        destination_balance = new_destination_balance

    # -------------------------------------------------------------
    # Inject final adversarial bust-out event
    # -------------------------------------------------------------

    attack_index = max(
        1,
        min(
            number_of_transactions - 1,
            int(number_of_transactions * 0.75)
            + int(strike_week_offset)
        )
    )

    history_spends = [
        float(event["spend"])
        for event in timeline[:attack_index]
    ]

    mean_spend = (
        sum(history_spends) /
        max(1, len(history_spends))
    )

    attack_amount = mean_spend * float(
        surge_multiplier_cap
    )

    attack_amount = max(
        float(min_amount),
        attack_amount
    )

    attack_amount = min(
        attack_amount,
        max(balance, attack_amount)
    )

    attack_transaction = {
        "account_id": account_id,
        "step": attack_index,
        "type": "CASH_OUT",
        "amount": round(attack_amount, 2),
        "nameOrig": account_id,
        "nameDest": (
            "D-" +
            str(random.randint(10000, 99999))
        ),
        "oldbalanceOrg": round(balance, 2),
        "newbalanceOrig": round(
            max(0.0, balance - attack_amount),
            2
        ),
        "oldbalanceDest": round(
            destination_balance,
            2
        ),
        "newbalanceDest": round(
            destination_balance + attack_amount,
            2
        ),
        "is_attack": True
    }

    timeline[attack_index - 1] = {
        "step": attack_index,
        "day": attack_index,
        "sequence": attack_index,
        "phase": "ATTACK",

        "spend": round(attack_amount, 2),
        "login_count": max(
            0,
            3 + random.randint(
                -int(login_jitter),
                int(login_jitter)
            )
        ),
        "new_device": False,

        "transaction": attack_transaction,

        "fraud_strike": True,
        "attack_type": "SYNTHETIC_IDENTITY",
        "severity": "HIGH"
    }

    return timeline