import subprocess
import sys
from pathlib import Path
from modules.utils.custom_print import print_log



def pip_install_package(requirements_file: str = "requirements.txt") -> bool:
    if not requirements_file:
        print_log("No requirements file provided.")
        return False

    requirements_path = Path(requirements_file)

    if not requirements_path.exists():
        print_log(f"Requirements file not found: {requirements_path}")
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

def package_runner() -> bool:
    if pip_install_package():
        print_log("Packages installed successfully.")
        return True
    else:
        print_log("Failed to install packages.")
        return False


if __name__ == "__main__":
    if pip_install_package():
        print_log("Packages installed successfully.")
    else:
        print_log("Failed to install packages.")