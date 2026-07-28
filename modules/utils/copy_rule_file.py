import shutil
from pathlib import Path
from modules.utils.custom_print import print_log



PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_FOLDER = PROJECT_ROOT / "datas" / "rule"
OUTPUT_FOLDER = PROJECT_ROOT / "datas" / "data_files"


def copy_rule_file() -> Path:
    source_file = SOURCE_FOLDER / "rule.txt"
    destination_file = OUTPUT_FOLDER / "rule.txt"

    if not source_file.is_file():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ต้นทาง: {source_file}"
        )

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source_file,
        destination_file,
    )

    return destination_file


if __name__ == "__main__":
    copied_file = copy_rule_file()
    print_log(f"คัดลอกไฟล์สำเร็จ: {copied_file}")