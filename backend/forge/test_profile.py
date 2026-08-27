from backend.forge.dataset_loader import load_paysim_data
from backend.forge.transaction_profile import build_paysim_profile


def main():

    print("Loading PaySim...")

    df = load_paysim_data()

    profile = build_paysim_profile(df)

    profile.show()


if __name__ == "__main__":
    main()