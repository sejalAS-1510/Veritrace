import random


def inject_sleeper_attack(
    history,
    attack_start_step=721
):

    attacked_history = []

    for transaction in history:

        attacked_history.append(
            transaction.copy()
        )

    attack_transactions = []

    for i in range(10):

        step = (
            attack_start_step + i
        )

        amount = random.randint(
            50000,
            200000
        )

        attack_transaction = {

            "account_id":
                history[0]["account_id"],

            "step":
                step,

            "type":
                random.choice(
                    [
                        "TRANSFER",
                        "CASH_OUT"
                    ]
                ),

            "amount":
                amount,

            "nameOrig":
                history[0]["account_id"],

            "nameDest":
                "ATTACK-" +
                str(
                    random.randint(
                        10000,
                        99999
                    )
                ),

            "oldbalanceOrg":
                0,

            "newbalanceOrig":
                0,

            "oldbalanceDest":
                0,

            "newbalanceDest":
                amount,

            "is_attack":
                True
        }

        attack_transactions.append(
            attack_transaction
        )

    return (
        attacked_history +
        attack_transactions
    )