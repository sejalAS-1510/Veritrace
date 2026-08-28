from backend.forge.sleeper_agent import inject_sleeper_attack


def main():

    history = []

    balance = 500000

    for step in range(1, 21):

        transaction = {
            "account_id": "SYN-TEST",
            "step": step,
            "type": "PAYMENT",
            "amount": 1000,
            "nameOrig": "SYN-TEST",
            "nameDest": f"DEST-{step}",
            "oldbalanceOrg": balance,
            "newbalanceOrig": balance - 1000,
            "oldbalanceDest": 0,
            "newbalanceDest": 1000,
            "is_attack": False
        }

        balance -= 1000
        history.append(transaction)

    attacked_history = inject_sleeper_attack(
        history,
        attack_start_step=21,
        number_of_attack_transactions=10
    )

    print("Attack Injection Test")
    print("--------------------------------")

    print("Original transactions:", len(history))
    print("Final transactions:", len(attacked_history))

    attack_events = [
        transaction
        for transaction in attacked_history
        if transaction.get("is_attack") is True
    ]

    print("Attack transactions:", len(attack_events))

    for transaction in attack_events:
        print(
            "STEP:",
            transaction["step"],
            "| TYPE:",
            transaction["type"],
            "| AMOUNT:",
            transaction["amount"],
            "| DEST:",
            transaction["nameDest"],
            "| ATTACK:",
            transaction["is_attack"]
        )

    assert len(attacked_history) == 30
    assert len(attack_events) == 10

    print("--------------------------------")
    print("Attack injection validation PASSED")


if __name__ == "__main__":
    main()