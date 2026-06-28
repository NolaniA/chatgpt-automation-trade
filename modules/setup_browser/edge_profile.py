import subprocess
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Literal
from modules.utils.custom_print import print_log



def find_edge_executable() -> Path | None:
    possible_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path.home() / r"AppData\Local\Microsoft\Edge\Application\msedge.exe",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None

def kill_edge_processes():
    subprocess.run(
        ["taskkill", "/F", "/IM", "msedge.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_cdp(debug_port: int = 9222, timeout: int = 10) -> bool:
    url = f"http://localhost:{debug_port}/json/version"
    start = time.time()

    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)

    return False


def setup_edge_profile(
    mode: Literal["new_profile", "clone_profile"] = "new_profile",
    path_edge_execute: Path | None = None,
    debug_port: int = 9222,
    playwright_profile_folder: Path = Path(r"C:\edge-playwright-profile"),
    source_user_data_dir: Path | None = None,
    source_profile_folder: str = "Default",
    target_profile_folder: str = "Default",
):
    if mode not in ["new_profile", "clone_profile"]:
        raise ValueError("mode must be 'new_profile' or 'clone_profile'")

    if path_edge_execute is None:
        path_edge_execute = find_edge_executable()

    while path_edge_execute is None or not path_edge_execute.exists():
        user_input = input(
            "Microsoft Edge executable not found.\n"
            "Open edge://version and copy Executable path here: "
        )
        path_edge_execute = Path(user_input.strip().strip('"'))

    if not isinstance(debug_port, int):
        raise ValueError("debug_port must be integer, example: 9222")

    # ปิด Edge ก่อน เพื่อกัน profile lock และกัน instance เดิมกิน port
    kill_edge_processes()

    playwright_profile_folder.mkdir(parents=True, exist_ok=True)

    if mode == "clone_profile":
        if source_user_data_dir is None:
            user_input = input(
                "Open edge://version and copy Profile path.\n"
                "Example:\n"
                r"C:\Users\YOUR_USER\AppData\Local\Microsoft\Edge\User Data\Default"
                "\n\nEnter Profile path: "
            )

            profile_path = Path(user_input.strip().strip('"'))

            source_user_data_dir = profile_path.parent
            source_profile_folder = profile_path.name

        source_profile_path = source_user_data_dir / source_profile_folder
        target_profile_path = playwright_profile_folder / target_profile_folder

        if not source_profile_path.exists():
            raise FileNotFoundError(f"Source profile not found: {source_profile_path}")

        if target_profile_path.exists():
            print_log(f"Target profile already exists: {target_profile_path}")
            print_log("Skip clone.")
        else:
            print_log("Cloning profile:")
            print_log(f"FROM: {source_profile_path}")
            print_log(f"TO:   {target_profile_path}")

            shutil.copytree(
                source_profile_path,
                target_profile_path,
                ignore=shutil.ignore_patterns(
                    "SingletonLock",
                    "SingletonCookie",
                    "SingletonSocket",
                    "LOCK",
                    "lockfile",
                    "Crashpad",
                    "Code Cache",
                    "GPUCache",
                    "ShaderCache",
                    "GrShaderCache",
                    "DawnCache",
                    "BrowserMetrics",
                    "Safe Browsing",
                    "OptimizationGuidePredictionModels",
                ),
            )

    args = [
        str(path_edge_execute),
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={playwright_profile_folder}",
        f"--profile-directory={target_profile_folder}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    print_log("Starting Edge:")
    print_log(" ".join(f'"{x}"' if " " in x else x for x in args))

    process = subprocess.Popen(args)

    if wait_for_cdp(debug_port):
        print_log(f"CDP ready: http://localhost:{debug_port}/json/version", end="\r")
    else:
        print_log(f"Warning: CDP not ready on port {debug_port}", end="\r")

    return process

if __name__ == "__main__":
    process = setup_edge_profile()
    print_log(f"Edge process started with PID: {process.pid}")
