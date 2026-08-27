from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "reference"


def load_paysim_data():
    file_path = DATA_DIR / "paysim.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"PaySim dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def load_training_data():
    file_path = DATA_DIR / "transactions_train.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def load_test_data():
    file_path = DATA_DIR / "transactions_test.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)