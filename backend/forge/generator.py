import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

try:
    from backend.forge.dataset_loader import load_paysim_data
    from backend.forge.profile_generator import generate_profile
    from backend.forge.transaction_profile import build_paysim_profile
    from backend.forge.history_generator import generate_history
    from backend.forge.feature_extractor import extract_features
except ImportError:
    try:
        from forge.dataset_loader import load_paysim_data
        from forge.profile_generator import generate_profile
        from forge.transaction_profile import build_paysim_profile
        from forge.history_generator import generate_history
        from forge.feature_extractor import extract_features
    except ImportError:
        pass

try:
    from faker import Faker
    fake = Faker("en_IN")
except ImportError:
    fake = None


MERCHANTS = [
    ("FreshMart", "GROCERY"),
    ("Food Corner", "RESTAURANT"),
    ("City Utilities", "UTILITY"),
    ("Metro Store", "SHOPPING"),
    ("QuickRide", "TRANSPORT"),
    ("Movie World", "ENTERTAINMENT"),
    ("Health Plus", "MEDICAL"),
]


CITIES = [
    "Pune",
    "Mumbai",
    "Nashik",
    "Bangalore",
    "Hyderabad",
]


def create_account():
    """Create a synthetic customer profile."""

    account_id = "SYN-" + uuid.uuid4().hex[:6].upper()

    account = {
        "account_id": account_id,
        "name": fake.name(),
        "age": random.randint(22, 55),
        "city": random.choice(CITIES),
        "occupation": fake.job(),
        "income": random.randint(35000, 120000),
        "credit_limit": random.randint(75000, 250000),
        "created_at": datetime.now().isoformat(),

        # These will be used while generating behavior.
        "primary_device": "DEV-" + uuid.uuid4().hex[:6].upper(),
    }

    return account


def create_transaction(account_id, day, city, device_id):
    """Create one normal purchase transaction."""

    merchant, category = random.choice(MERCHANTS)

    transaction = {
        "transaction_id": "TX-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account_id,
        "day": day,
        "amount": random.randint(200, 5000),
        "merchant": merchant,
        "merchant_category": category,
        "location": city,
        "device_id": device_id,
        "transaction_type": "PURCHASE",
    }

    return transaction


def create_transactions(account, number_of_days=180):
    """
    Generate normal transactions across the account lifetime.

    Not every day contains a transaction.
    """

    transactions = []

    for day in range(1, number_of_days + 1):

        # Around 30% of days contain normal spending.
        if random.random() > 0.30:
            continue

        transaction = create_transaction(
            account_id=account["account_id"],
            day=day,
            city=account["city"],
            device_id=account["primary_device"],
        )

        transactions.append(transaction)

    return transactions


def save_json(data, filename):
    """Save data inside data/generated."""

    output_folder = Path("data/generated")
    output_folder.mkdir(parents=True, exist_ok=True)

    file_path = output_folder / filename

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    return file_path

def generate_account_history(
    number_of_transactions=200
):

    # ---------------------------------------
    # Load reference data
    # ---------------------------------------

    paysim = load_paysim_data()

    transaction_profile = build_paysim_profile(
        paysim
    )

    # ---------------------------------------
    # Generate synthetic identity
    # ---------------------------------------

    profile = generate_profile()

    # ---------------------------------------
    # Generate behavioral history
    # ---------------------------------------

    destination_balance = 50000

    history = generate_history(

        account_id=profile["account_id"],

        starting_balance=profile[
            "starting_balance"
        ],

        destination_balance=destination_balance,

        transaction_types=transaction_profile.transaction_types ,

        average_amount=transaction_profile.average_amount,

        min_amount=transaction_profile.min_amount,

        max_amount=transaction_profile.max_amount, 

        number_of_transactions= number_of_transactions
    )

    features = extract_features(
    history
)

    return {
        "profile": profile,
        "history": history,
        "features": features
    }


def print_account(account):

    profile = account["profile"]
    history = account["history"]

    print()
    print("=" * 60)
    print("                 FORGE")
    print("=" * 60)

    print()
    print("ACCOUNT CREATED")
    print("-" * 40)

    print(
        "Account ID:",
        profile["account_id"]
    )

    print(
        "Name:",
        profile["name"]
    )

    print(
        "City:",
        profile["city"]
    )

    print(
        "Income:",
        f"₹{profile['income']}"
    )

    print(
        "Starting balance:",
        f"₹{profile['starting_balance']}"
    )

    print(
        "Device:",
        profile["device_id"]
    )

    print()
    print("BEHAVIORAL HISTORY")
    print("-" * 40)

    print(
        "Total transactions:",
        len(history)
    )

    print()
    print("BEHAVIORAL FEATURES")
    print("-" * 40)

    for key, value in account["features"].items():

     print(
        f"{key}: {value}"
    )

    print()

    for transaction in history[:10]:

        print(
            f"Day {transaction['step']:>3} | "
            f"{transaction['type']:<10} | "
            f"₹{transaction['amount']:>10.2f} | "
            f"Balance: ₹{transaction['newbalanceOrig']:.2f}"
        )


def main():

    print()
    print("Starting Forge...")

    account = generate_account_history(
        number_of_transactions=200
    )

    print_account(account)
    

def generate_timeline_adversarial(
    weeks: int = 24,
    ring_id: Optional[str] = None,
    noise_factor: float = 0.035,
    dip_probability: float = 0.04,
    dip_magnitude: float = 0.15,
    login_jitter: int = 1,
    ramp_rate_variance: float = 0.05,
    strike_week_offset: int = 0,
    base_spend_offset: float = 0.0,
    surge_multiplier_cap: float = 20.0,
    **kwargs
) -> Dict[str, Any]:
    """Generates an adversarial sleeper timeline parameterized by mutation engine."""
    identity_id = f"VT-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    if ring_id:
        base_spend = 120.0 + (hash(ring_id) % 50) + base_spend_offset
        ramp_rate = 14.0 + ((hash(ring_id) >> 2) % 6)
        base_login = 5
    else:
        base_spend = float(np.random.uniform(90.0, 180.0)) + base_spend_offset
        ramp_rate = float(np.random.uniform(10.0, 22.0))
        base_login = int(np.random.choice([4, 5, 6]))

    strike_week = max(4, min(weeks, 24 + strike_week_offset))

    for w in range(1, weeks + 1):
        if w < strike_week:
            noise = float(np.random.normal(0, max(1.0, base_spend * noise_factor)))
            ramp_noise = float(np.random.normal(0, max(0.1, ramp_rate * ramp_rate_variance)))
            spend = max(20.0, base_spend + (w - 1) * (ramp_rate + ramp_noise) + noise)
            
            if random.random() < dip_probability:
                spend *= (1.0 - dip_magnitude)
            spend = round(float(spend), 2)

            jitter = int(np.random.randint(-login_jitter, login_jitter + 1)) if login_jitter > 0 else 0
            login_count = max(1, int(base_login + jitter))

            new_device = bool(random.random() < 0.03)
            location_change = bool(random.random() < 0.02)
            bill_paid_on_time = True
            fraud_strike = False
        else:
            pre_strike_avg = base_spend + (strike_week - 1) * ramp_rate
            min_surge = min(3.5, surge_multiplier_cap)
            max_surge = max(min_surge + 0.5, surge_multiplier_cap)
            surge_mult = float(np.random.uniform(min_surge, max_surge))
            spend = round(pre_strike_avg * surge_mult + float(np.random.normal(500, 100)), 2)

            login_count = int(np.random.randint(18, 36))
            new_device = True
            location_change = True
            bill_paid_on_time = False
            fraud_strike = True

        timeline.append({
            "week": w,
            "spend": float(spend),
            "login_count": int(login_count),
            "new_device": new_device,
            "location_change": location_change,
            "bill_paid_on_time": bill_paid_on_time,
            "fraud_strike": fraud_strike
        })

    return {
        "id": identity_id,
        "type": "sleeper",
        "ring_id": ring_id,
        "timeline": timeline,
        "weeks_count": weeks
    }


def generate_timeline(
    identity_type: Optional[str] = None,
    weeks: int = 24,
    seed: Optional[int] = None,
    ring_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Generates a 24-week timeline for sleeper or benign organic identity."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    if identity_type is None:
        identity_type = "sleeper" if random.random() < 0.5 else "benign"

    if identity_type == "sleeper":
        return generate_timeline_adversarial(weeks=weeks, ring_id=ring_id, **kwargs)

    identity_id = f"VT-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    baseline_spend = float(np.random.uniform(220.0, 650.0))
    volatility = float(np.random.uniform(0.20, 0.45))

    for w in range(1, weeks + 1):
        random_factor = float(np.random.lognormal(mean=0, sigma=volatility))
        cycle = 1.0 + 0.15 * np.sin(w * 2 * np.pi / 4.3)
        spend = max(15.0, round(baseline_spend * random_factor * cycle, 2))

        login_count = max(0, int(np.random.poisson(lam=5.5) + np.random.randint(-1, 3)))
        new_device = bool(random.random() < 0.08)
        location_change = bool(random.random() < 0.09)
        bill_paid_on_time = bool(random.random() > 0.08)
        fraud_strike = False

        timeline.append({
            "week": w,
            "spend": float(spend),
            "login_count": int(login_count),
            "new_device": new_device,
            "location_change": location_change,
            "bill_paid_on_time": bill_paid_on_time,
            "fraud_strike": fraud_strike
        })

    return {
        "id": identity_id,
        "type": "benign",
        "ring_id": ring_id,
        "timeline": timeline,
        "weeks_count": weeks
    }


def generate_batch(count: int = 10, sleeper_ratio: float = 0.5) -> List[Dict[str, Any]]:
    """Generates a batch of identities with a realistic mix including a fraud ring cluster."""
    identities = []
    ring_size = min(4, max(3, int(count * 0.35)))
    ring_tag = f"RING-{uuid.uuid4().hex[:4].upper()}"

    for _ in range(ring_size):
        identities.append(generate_timeline(identity_type="sleeper", ring_id=ring_tag))

    remaining = count - ring_size
    for _ in range(remaining):
        itype = "sleeper" if random.random() < sleeper_ratio else "benign"
        identities.append(generate_timeline(identity_type=itype))

    return identities

