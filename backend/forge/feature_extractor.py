import statistics


def extract_features(history):

    if not history:
        return {}

    amounts = [
        transaction["amount"]
        for transaction in history
    ]

    transaction_types = [
        transaction["type"]
        for transaction in history
    ]

    # Total money involved in the account history
    total_amount = sum(amounts)

    # Average transaction size
    average_amount = (
        total_amount / len(amounts)
    )

    # Standard deviation tells us how much
    # transaction amounts vary.
    amount_volatility = statistics.pstdev(
        amounts
    )

    # Calculate how long the history spans.
    first_step = history[0]["step"]
    last_step = history[-1]["step"]

    active_days = (
        last_step - first_step + 1
    )

    # Count each transaction type.
    type_counts = {}

    for transaction_type in transaction_types:

        type_counts[transaction_type] = (
            type_counts.get(
                transaction_type,
                0
            ) + 1
        )

    # Transactions per active day.
    transaction_velocity = (
        len(history) /
        max(active_days, 1)
    )

    features = {

        "transaction_count":
            len(history),

        "total_transaction_amount":
            round(
                total_amount,
                2
            ),

        "average_transaction_amount":
            round(
                average_amount,
                2
            ),

        "amount_volatility":
            round(
                amount_volatility,
                2
            ),

        "active_days":
            active_days,

        "transaction_velocity":
            round(
                transaction_velocity,
                4
            ),

        "transaction_type_counts":
            type_counts
    }

    return features