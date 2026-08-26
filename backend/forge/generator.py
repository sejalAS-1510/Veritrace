import json
import random
import uuid
from datetime import datetime
from pathlib import Path

from faker import Faker


fake = Faker("en_IN")


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


if __name__ == "__main__":

    print("Starting Forge...\n")

    account = create_account()

    transactions = create_transactions(account)

    save_json(account, "accounts.json")
    save_json(transactions, "transactions.json")

    print("Account created")
    print("-------------------------")
    print(f"Account ID : {account['account_id']}")
    print(f"Name       : {account['name']}")
    print(f"City       : {account['city']}")
    print(f"Income     : ₹{account['income']}")
    print(f"Credit     : ₹{account['credit_limit']}")
    print(f"Device     : {account['primary_device']}")
    print()
    print(f"Transactions generated: {len(transactions)}")

