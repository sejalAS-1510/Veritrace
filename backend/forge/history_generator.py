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

    history.append(transaction)

    step += random.randint(
            1,
            5
        )

    return history