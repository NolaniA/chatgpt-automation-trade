import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FOLDER = PROJECT_ROOT / "datas" / "data_files"


def save_json(
    file_name: str,
    data: Any,
) -> bool:
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("file_name must be a non-empty string")

    file_name = file_name.strip()

    if not file_name.lower().endswith(".json"):
        file_name = f"{file_name}.json"

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_FOLDER / file_name

    try:
        with output_file.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        return True

    except (OSError, TypeError, ValueError) as error:
        print_log(
            f"Failed to save JSON file "
            f"'{output_file}': {error}"
        )
        return False