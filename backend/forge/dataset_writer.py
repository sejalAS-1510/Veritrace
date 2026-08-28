import json
from pathlib import Path


def save_accounts(
    accounts,
    filename="forge_output.json"
):

    output_dir = Path("data")

    output_dir.mkdir(
        exist_ok=True
    )

    output_file = (
        output_dir / filename
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            accounts,
            file,
            indent=2
        )

    print()
    print(
        "Forge dataset saved to:",
        output_file
    )