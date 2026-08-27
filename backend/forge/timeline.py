import json
import random
import uuid
from pathlib import Path
from dataclasses import dataclass

from backend.forge.config import (
    ACCOUNT_AGE_DAYS,
    LOGIN_DAY_PROBABILITY,
)


MERCHANTS = [
    ("FreshMart", "GROCERY"),
    ("Food Corner", "RESTAURANT"),
    ("Metro Store", "SHOPPING"),
    ("QuickRide", "TRANSPORT"),
    ("Movie World", "ENTERTAINMENT"),
    ("Health Plus", "MEDICAL"),
]

from dataclasses import dataclass


@dataclass
class TimelinePhase:
    name: str
    start_step: int
    end_step: int
    activity_multiplier: float
    amount_multiplier: float


def build_normal_timeline():

    return [

        TimelinePhase(
            name="EARLY_LIFE",
            start_step=1,
            end_step=120,
            activity_multiplier=0.7,
            amount_multiplier=0.8
        ),

        TimelinePhase(
            name="NORMAL",
            start_step=121,
            end_step=500,
            activity_multiplier=1.0,
            amount_multiplier=1.0
        ),

        TimelinePhase(
            name="MATURE",
            start_step=501,
            end_step=700,
            activity_multiplier=1.1,
            amount_multiplier=1.1
        ),

        TimelinePhase(
            name="DORMANT",
            start_step=701,
            end_step=720,
            activity_multiplier=0.1,
            amount_multiplier=0.5
        )
    ]


def create_devices(account):
    """Create a small set of devices for the account."""

    devices = [
        account["primary_device"]
    ]

    # Most customers have one or two additional devices.
    number_of_extra_devices = random.choice([0, 1, 2])

    for _ in range(number_of_extra_devices):
        device_id = "DEV-" + uuid.uuid4().hex[:6].upper()
        devices.append(device_id)

    return devices


def create_transaction(account, day, device_id):
    """Create a normal purchase event."""

    merchant, category = random.choice(MERCHANTS)

    return {
        "event_id": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account["account_id"],
        "day": day,
        "event_type": "TRANSACTION",
        "amount": random.randint(200, 5000),
        "merchant": merchant,
        "merchant_category": category,
        "location": account["city"],
        "device_id": device_id,
    }


def create_bill_payment(account, day, device_id):
    """Create a regular monthly bill payment."""

    bills = [
        ("Electricity", random.randint(800, 2500)),
        ("Internet", random.randint(500, 1500)),
        ("Mobile", random.randint(300, 1000)),
        ("Water", random.randint(300, 900)),
    ]

    bill_name, amount = random.choice(bills)

    return {
        "event_id": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account["account_id"],
        "day": day,
        "event_type": "BILL_PAYMENT",
        "amount": amount,
        "merchant": bill_name,
        "location": account["city"],
        "device_id": device_id,
    }


def create_salary_credit(account, day):
    """Create a salary-like monthly credit."""

    return {
        "event_id": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account["account_id"],
        "day": day,
        "event_type": "SALARY_CREDIT",
        "amount": account["income"],
        "merchant": "Employer",
        "location": account["city"],
        "device_id": None,
    }


def create_login(account, day, device_id):
    """Create a login event."""

    login_hours = [8, 9, 10, 12, 18, 19, 20, 21, 22]

    return {
        "event_id": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account["account_id"],
        "day": day,
        "event_type": "LOGIN",
        "login_hour": random.choice(login_hours),
        "location": account["city"],
        "device_id": device_id,
    }


def create_device_change(account, day, new_device):
    """Record a new device being used."""

    return {
        "event_id": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "account_id": account["account_id"],
        "day": day,
        "event_type": "DEVICE_CHANGE",
        "device_id": new_device,
        "location": account["city"],
    }


def create_timeline(account):
    """
    Generate a 180-day behavioral timeline.

    The timeline contains normal activity such as:
    transactions, logins, bills and salary credits.
    """

    devices = create_devices(account)

    timeline = []

    for day in range(1, ACCOUNT_AGE_DAYS + 1):

        current_device = random.choice(devices)

        # Login behavior
        if random.random() < LOGIN_DAY_PROBABILITY:

            login = create_login(
                account,
                day,
                current_device
            )

            timeline.append(login)

        # Normal spending
        if random.random() < 0.30:

            transaction = create_transaction(
                account,
                day,
                current_device
            )

            timeline.append(transaction)

        # Monthly bill payment
        if day % 30 == random.randint(1, 5):

            bill = create_bill_payment(
                account,
                day,
                current_device
            )

            timeline.append(bill)

        # Salary-like credit once a month
        if day % 30 == 1:

            salary = create_salary_credit(
                account,
                day
            )

            timeline.append(salary)

        # Device change occasionally happens.
        if day in [60, 120]:

            new_device = random.choice(devices)

            device_event = create_device_change(
                account,
                day,
                new_device
            )

            timeline.append(device_event)

    return timeline


def save_timeline(timeline):
    """Save timeline as JSON."""

    output_folder = Path("data/generated")
    output_folder.mkdir(parents=True, exist_ok=True)

    file_path = output_folder / "timeline.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(timeline, file, indent=4)

    return file_path

def create_credit_utilization(account):
    """
    Create a monthly credit-utilization history.

    Normal utilization slowly changes over time.
    """

    utilization = []

    current_usage = random.randint(10, 25)

    for month in range(1, 7):

        # Small natural variation.
        change = random.randint(-4, 6)

        current_usage += change

        # Keep normal utilization within a reasonable range.
        current_usage = max(5, min(current_usage, 50))

        utilization.append({
            "account_id": account["account_id"],
            "month": month,
            "utilization_percent": current_usage
        })

    return utilization

