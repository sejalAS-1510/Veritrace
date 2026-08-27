from backend.forge.profile_generator import generate_profile


def main():

    print()
    print("=" * 50)
    print("        SYNTHETIC PROFILE TEST")
    print("=" * 50)

    profile = generate_profile()

    for key, value in profile.items():

        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":
    main()