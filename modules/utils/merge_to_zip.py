from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from modules.utils.custom_print import print_log


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_FOLDER = PROJECT_ROOT / "datas" / "data_files"
OUTPUT_FOLDER = PROJECT_ROOT / "datas" / "data_zip"


def create_zip_file(
    file_name: str = "upload.zip",
    target_folder: Path = TARGET_FOLDER,
    output_folder: Path = OUTPUT_FOLDER,
) -> Path:
    if not file_name or not file_name.strip():
        raise ValueError("file_name must not be empty")

    file_name = file_name.strip()

    if Path(file_name).suffix.lower() != ".zip":
        file_name = f"{file_name}.zip"

    if not target_folder.exists():
        raise FileNotFoundError(
            f"Target folder does not exist: {target_folder}"
        )

    if not target_folder.is_dir():
        raise NotADirectoryError(
            f"Target path is not a directory: {target_folder}"
        )

    output_folder.mkdir(parents=True, exist_ok=True)

    zip_path = output_folder / file_name
    temp_zip_path = output_folder / f".{zip_path.stem}.tmp.zip"

    files = [
        path
        for path in target_folder.rglob("*")
        if path.is_file()
    ]

    if not files:
        raise RuntimeError(
            f"No files found in target folder: {target_folder}"
        )

    try:
        if temp_zip_path.exists():
            temp_zip_path.unlink()

        with ZipFile(
            temp_zip_path,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as zip_file:
            for file_path in files:
                arcname = file_path.relative_to(target_folder)

                zip_file.write(
                    file_path,
                    arcname=arcname,
                )


                print_log(f"Add to zip: {arcname}")

        if zip_path.exists():
            zip_path.unlink()

        temp_zip_path.replace(zip_path)

    except PermissionError as error:
        raise RuntimeError(
            f"Cannot replace ZIP file. File may be open or locked: {zip_path}"
        ) from error

    except OSError as error:
        raise RuntimeError(
            f"Failed to create ZIP file '{zip_path}': {error}"
        ) from error

    return zip_path


if __name__ == "__main__":
    created_zip = create_zip_file()
    print_log(f"ZIP file created: {created_zip}")