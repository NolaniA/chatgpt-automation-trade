import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Literal

from modules.utils.custom_print import print_log


EDGE_PROFILE_ROOT = Path(r"C:\edge-playwright-profile")
EDGE_PROFILE_NAME = "Default"
EDGE_DEBUG_PORT = 9222


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
    subprocess.run( ["taskkill", "/F", "/IM", "msedge.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, )


def wait_for_cdp(debug_port: int = 9222, timeout: float = 10) -> bool:
    url = f"http://127.0.0.1:{debug_port}/json/version"
    start = time.time()

    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)

    return False


def clone_profile_once(
    target_user_data_dir: Path,
    target_profile_folder: str,
    source_user_data_dir: Path | None = None,
    source_profile_folder: str = "Default",
) -> None:
    target_profile_path = target_user_data_dir / target_profile_folder

    # มี profile แล้ว ใช้ของเดิมทันที ไม่ถาม source path ซ้ำ
    if target_profile_path.exists():
        print_log(f"Reuse existing profile: {target_profile_path}")
        return

    if source_user_data_dir is None:
        user_input = input(
            "Open edge://version and copy Profile path.\n"
            "Example:\n"
            r"C:\Users\YOUR_USER\AppData\Local\Microsoft\Edge\User Data\Default"
            "\n\nEnter Profile path: "
        )

        source_profile_path = Path(user_input.strip().strip('"'))
        source_user_data_dir = source_profile_path.parent
        source_profile_folder = source_profile_path.name

    source_profile_path = source_user_data_dir / source_profile_folder

    if not source_profile_path.exists():
        raise FileNotFoundError(
            f"Source profile not found: {source_profile_path}"
        )

    target_user_data_dir.mkdir(parents=True, exist_ok=True)

    print_log("Cloning Edge profile:")
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

    # สำคัญสำหรับข้อมูล encryption/login บางส่วนของ Chromium
    source_local_state = source_user_data_dir / "Local State"
    target_local_state = target_user_data_dir / "Local State"

    if source_local_state.exists() and not target_local_state.exists():
        shutil.copy2(source_local_state, target_local_state)

    print_log("Profile cloned successfully.")


def setup_edge_profile(
    mode: Literal["new_profile", "clone_profile"] = "clone_profile",
    path_edge_execute: Path | None = None,
    debug_port: int = EDGE_DEBUG_PORT,
    playwright_profile_folder: Path = EDGE_PROFILE_ROOT,
    source_user_data_dir: Path | None = None,
    source_profile_folder: str = "Default",
    target_profile_folder: str = EDGE_PROFILE_NAME,
) -> subprocess.Popen | None:
    if mode not in {"new_profile", "clone_profile"}:
        raise ValueError(
            "mode must be 'new_profile' or 'clone_profile'"
        )

    if not isinstance(debug_port, int):
        raise TypeError("debug_port must be integer, example: 9222")

    # Edge profile ตัวนี้เปิดอยู่แล้ว ไม่ต้องเปิด process ใหม่
    if wait_for_cdp(debug_port, timeout=1):
        print_log(
            f"Reuse running Edge CDP: "
            f"http://127.0.0.1:{debug_port}"
        )
        return None

    if path_edge_execute is None:
        path_edge_execute = find_edge_executable()

    while path_edge_execute is None or not path_edge_execute.exists():
        user_input = input(
            "Microsoft Edge executable not found.\n"
            "Open edge://version and copy Executable path here: "
        )
        path_edge_execute = Path(user_input.strip().strip('"'))

    playwright_profile_folder.mkdir(parents=True, exist_ok=True)

    if mode == "clone_profile":
        clone_profile_once(
            target_user_data_dir=playwright_profile_folder,
            target_profile_folder=target_profile_folder,
            source_user_data_dir=source_user_data_dir,
            source_profile_folder=source_profile_folder,
        )

    args = [
        str(path_edge_execute),
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={playwright_profile_folder}",
        f"--profile-directory={target_profile_folder}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    process = subprocess.Popen(args)

    if not wait_for_cdp(debug_port):
        process.terminate()
        raise RuntimeError(
            f"CDP not ready on port {debug_port}"
        )

    print_log(
        f"CDP ready: http://127.0.0.1:{debug_port}/json/version"
    )

    return process


if __name__ == "__main__":
    process = setup_edge_profile(
        mode="clone_profile",
        playwright_profile_folder=EDGE_PROFILE_ROOT,
        target_profile_folder=EDGE_PROFILE_NAME,
    )

    if process is None:
        print_log("Edge is already running with the saved profile.")
    else:
        print_log(f"Edge started with PID: {process.pid}")