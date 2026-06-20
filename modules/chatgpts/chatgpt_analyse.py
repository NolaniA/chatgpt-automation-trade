import os
import time
import webbrowser
from pathlib import Path
from dataclasses import dataclass
import shutil
import zipfile


import pyautogui
import pyperclip
# from dotenv import load_dotenv


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


class ChatGPTUploader:
    def __init__(self, config: ChatGPTUploaderConfig):
        self.cfg = config

        # กัน pyautogui หลุด: เอาเมาส์ไปมุมซ้ายบนเพื่อหยุดสคริปต์ทันที
        # pyautogui.FAILSAFE = True
        # pyautogui.PAUSE = 0.05

        self.url = self.cfg.url_gpt_project

        if not self.url:
            raise ValueError(f"Missing env var: {self.cfg.url_gpt_project}")

        if not self.cfg.data_folder.exists():
            raise FileNotFoundError(f"Data folder not found: {self.cfg.data_folder}")

    # -------------------------
    # Low-level helpers
    # -------------------------
    def _sleep(self, s: float | None = None):
        time.sleep(self.cfg.between_actions_sleep if s is None else s)

    def _paste(self, text: str):
        pyperclip.copy(text)
        self._sleep(0.2)
        pyautogui.hotkey("ctrl", "v")

    def _read_text(self, path: Path, encoding="utf-8") -> str:
        if not path.exists():
        # if not path:
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_text(encoding=encoding)

    # -------------------------
    # Steps
    # -------------------------
    def open_project_page(self):
        webbrowser.open(self.url)
        self._sleep(self.cfg.page_load_sleep)

    def clear_text_input(self):
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        self._sleep(0.2)

    def upload_files_via_add(self):
        folder = self.cfg.data_folder
        files = sorted([p.name for p in folder.iterdir() if p.is_file()])
        # print("Files:", files)

        for filename in files:
            # /
            self._paste("/")
            self._sleep(0.3)
            pyautogui.hotkey("ctrl", "enter")
            self._sleep(2)

            # focus address bar (file picker path)
            pyautogui.hotkey("ctrl", "l")
            self._sleep(0.5)

            # paste folder path
            self._paste(str(folder))
            self._sleep(0.3)
            pyautogui.hotkey("ctrl", "enter")
            self._sleep(0.7)

            # select file name box (Alt+N) แล้วพิมพ์ชื่อไฟล์
            pyautogui.hotkey("alt", "n")
            self._sleep(0.3)

            self._paste(filename)
            self._sleep(0.2)
            pyautogui.hotkey("ctrl", "enter")
            self._sleep(0.8)

        self._sleep(1)

    def upload_file_zip(self):
        folder = Path(self.cfg.data_folder)
        zip_dir = Path("data_zip")
        zip_dir.mkdir(exist_ok=True)
        filename = "data.zip"

        zip_path = (zip_dir / filename).resolve()

        # สร้าง zip
        with zipfile.ZipFile(zip_path, "w") as z:
            for p in folder.iterdir():
                if p.is_file():
                    z.write(p, arcname=p.name)

        # ===== upload แค่ไฟล์เดียว =====
        self._paste("/")
        self._sleep(0.3)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(1.5)

        pyautogui.hotkey("ctrl", "l")
        self._sleep(0.5)

        self._paste(str(zip_dir.resolve()))
        self._sleep(0.3)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(0.7)

        pyautogui.hotkey("alt", "n")
        self._sleep(0.3)

        self._paste(filename)
        self._sleep(0.2)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(0.8)

        self._sleep(1)





    def paste_prompt(self):
        prompt = self._read_text(self.cfg.prompt_path)

        if prompt is None:
            raise ValueError("prompt is empty")

        self._paste(prompt)
        self._sleep(2.0)
        # ถ้าจะส่งจริงค่อยเปิด
        # pyautogui.hotkey("ctrl", "enter")

    def open_devtools_console(self):
        pyautogui.hotkey("ctrl", "shift", "j")
        self._sleep(2.0)

    def allow_console_pasting(self):
        pyautogui.write("allow pasting", interval=0.01)
        self._sleep(1.0)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(1.0)

    def run_helper_js(self):
        functions = self._read_text(self.cfg.helper_js_path)
        self._paste(functions)
        self._sleep(0.3)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(0.8)

    def run_script_js(self):
        script = self._read_text(self.cfg.script_js_path)
        self._paste(script)
        self._sleep(0.2)
        pyautogui.hotkey("ctrl", "enter")
        self._sleep(0.2)

        # ปิด devtools (เหมือนของเดิม)
        pyautogui.hotkey("ctrl", "shift", "j")
        self._sleep(1.0)

    def wait_until_done_in_address_bar(self):
        start = time.time()
        while True:
            if time.time() - start >= self.cfg.wait_done_timeout:
                raise TimeoutError("⏰ JS did not signal DONE in time")

            pyautogui.hotkey("ctrl", "l")
            self._sleep(0.2)

            pyautogui.hotkey("ctrl", "c")
            self._sleep(0.2)
            text = pyperclip.paste()

            pyautogui.press("escape", presses=2, interval=0.5)

            # print(text)

            if text.endswith(self.cfg.done_suffix):
                break


    def move_file_result(self):
        # find result file in dir download
        if not self.cfg.download_folder.exists():
            raise FileNotFoundError(f"Download dir not found: {self.cfg.download_folder}")

        downloads = list(self.cfg.download_folder.glob("gpt_result*.json*"))

        if not downloads:
            raise FileNotFoundError(f"No files found in: {self.cfg.download_folder}")

        # Find the latest modified file
        latest_file = max(downloads, key=os.path.getmtime)

        # move to result folder
        self.cfg.output_folder.mkdir(parents=True, exist_ok=True)
        dest = self.cfg.output_folder / self.cfg.result_file

        if dest.exists():
            if dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)

        shutil.move(str(latest_file), str(dest))




    def close_tab(self):
        pyautogui.hotkey("ctrl", "w")

    # -------------------------
    # One-shot runner
    # -------------------------
    def run_all(self):
        try:
            self.open_project_page()
            self.clear_text_input()
            # self.upload_files_via_add()
            self.upload_file_zip()
            self.paste_prompt()
            self.open_devtools_console()
            self.allow_console_pasting()
            self.run_helper_js()
            self.run_script_js()
            self.wait_until_done_in_address_bar()
            self.close_tab()
            self.move_file_result()
        except   Exception as e:
            print(f"chat gpt analyse error: {e}")


if __name__ == "__main__":
    cfg = ChatGPTUploaderConfig()
    bot = ChatGPTUploader(cfg)
    bot.run_all()
