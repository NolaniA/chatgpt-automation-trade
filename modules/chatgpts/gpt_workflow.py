from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright


@dataclass
class ChatGPTUploaderConfig:
    url_gpt_project: str
    data_folder: Path = Path("/chatgpt-analyse/data_files")
    output_folder: Path = Path("/chatgpt-analyse/result_analyse")
    download_folder: Path = Path("C:/Users/Saeng/Downloads")
    prompt_path: Path = Path("prompt.txt")
    result_file: Path = Path("result_gpt.json")
    helper_js_path: Path = Path("script_console/helper.js")
    script_js_path: Path = Path("script_console/script.js")

    page_load_sleep: float = 10.0
    between_actions_sleep: float = 1.0

    wait_done_timeout: int = 300
    done_suffix: str = "script=DONE"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    settimeout = 60000  # ms
    browser.set_default_navigation_timeout(settimeout)

    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    url_gpt_project = "https://chatgpt.com/g/g-p-6a26d2dd360c8191a7f679ced3858d9d-investor/project"

    page.goto(url_gpt_project, wait_until="domcontentloaded")

    page.pause()





    # result_path = run_chatgpt_submit_and_save(
    #     page,
    #     output_file="gpt_result.json",
    # )

    # print("result:", result_path)