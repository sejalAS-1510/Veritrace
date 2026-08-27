from collections import Counter


class TransactionProfile:

    def __init__(self):
        self.transaction_types = []
        self.average_amount = 0
        self.min_amount = 0
        self.max_amount = 0

    def show(self):

        print()
        print("=" * 50)
        print("TRANSACTION PROFILE")
        print("=" * 50)

        print()
        print("Transaction types:")

        print(self.transaction_types)

        print()
        print("Average amount:", round(self.average_amount, 2))

        print()
        print("Minimum amount:", round(self.min_amount, 2))

        print()
        print("Maximum amount:", round(self.max_amount, 2))


def build_paysim_profile(df):

    profile = TransactionProfile()

    profile.transaction_types = list(
        df["type"].unique()
    )

    profile.average_amount = df["amount"].mean()

    profile.min_amount = df["amount"].min()

    profile.max_amount = df["amount"].max()

    return profile