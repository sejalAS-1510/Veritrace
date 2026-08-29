FEATURES = [
    "transaction_amount",
    "account_age",
    "transaction_count",
    "avg_transaction_amount",
    "std_transaction_amount",
    "max_transaction_amount",
    "avg_time_gap",
    "std_time_gap",
    "transaction_type_diversity",
    "cash_out_ratio",
    "payment_ratio",
    "transfer_ratio",
    "debit_ratio",
    "avg_balance_change",
    "balance_change_std",
]

def benchmark_to_features(df):
    # Digital Payment Fraud Benchmark
    # customer_id = account
    # transaction_amount = amount
    # transaction_time = time
    pass


def forge_to_features(df):
    # Forge
    # account_id = account
    # amount = transaction amount
    # step = time
    # type = transaction type
    pass