from backend.forge.attack_scenarios import get_scenario


def main():

    print("Attack Scenario Test")
    print("--------------------------------")

    for severity in ["LOW", "MEDIUM", "HIGH"]:

        scenario = get_scenario(severity)

        print(f"\nSeverity: {severity}")
        print("Scenario:", scenario)

        assert scenario is not None

    print("\n--------------------------------")
    print("Attack scenario validation PASSED")


if __name__ == "__main__":
    main()