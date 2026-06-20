import subprocess
import sys
from pathlib import Path


def pip_install_package(requirements_file: str = "requirements.txt") -> bool:
    if not requirements_file:
        print("No requirements file provided.")
        return False

    requirements_path = Path(requirements_file)

    if not requirements_path.exists():
        print(f"Requirements file not found: {requirements_path}")
        return False

    result = subprocess.run([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(requirements_path),
    ])

    return result.returncode == 0


if __name__ == "__main__":
    if pip_install_package():
        print("Packages installed successfully.")
    else:
        print("Failed to install packages.")