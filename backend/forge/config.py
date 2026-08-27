# Number of days used for the sleeper-agent simulation.

ACCOUNT_AGE_DAYS = 180


# Probability that a normal day contains a transaction.

TRANSACTION_DAY_PROBABILITY = 0.30


# Probability of a login event on a particular day.

LOGIN_DAY_PROBABILITY = 0.70


# Amount used for the final cash-out attack.

DEFAULT_ATTACK_AMOUNT = 250000


# Number of devices an account can normally use.

MAX_NORMAL_DEVICES = 3

#Reference fields 
REFERENCE_FIELDS = [
    "customer_id",
    "transaction_time",
    "transaction_amount",
    "payment_channel",
    "device_type",
    "is_international",
    "ip_risk_score",
    "geo_distance_from_last_txn",
    "txn_count_1h",
    "txn_count_24h",
    "failed_txn_count_24h",
    "amount_deviation_from_user_mean",
    "account_age_days",
    "credit_score_band",
    "kyc_level",
    "avg_monthly_spend",
    "is_fraud",
]

IGNORED_FIELDS = [
    "merchant_id",
    "merchant_risk_score",
    "post_auth_risk_score",
]