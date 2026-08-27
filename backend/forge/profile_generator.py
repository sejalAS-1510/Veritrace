import random
import uuid

from faker import Faker


fake = Faker("en_IN")


def generate_account_id():
    return "SYN-" + uuid.uuid4().hex[:6].upper()


def generate_device_id():
    return "DEV-" + uuid.uuid4().hex[:6].upper()


def generate_profile():

    income = random.randint(20000, 150000)

    starting_balance = random.randint(
        50000,
        500000
    )

    profile = {
        "account_id": generate_account_id(),

        "name": fake.name(),

        "city": fake.city(),

        "income": income,

        "starting_balance": starting_balance,

        "device_id": generate_device_id(),

        "account_age_days": random.randint(
            180,
            720
        )
    }

    return profile