import json
from pathlib import Path
from typing import Optional
from modules.utils.custom_print import print_log

from playwright.sync_api import (
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    expect,
    sync_playwright,
)


class GptAnalyzer:
    def __init__(self, playwright: Playwright):
        self.playwright = playwright

        self.browser = self.playwright.chromium.connect_over_cdp(
            "http://localhost:9222"
        )

        if not self.browser.contexts:
            raise RuntimeError("ไม่พบ Browser Context จาก Edge")

        self.context = self.browser.contexts[0]

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        self.url_gpt_project = (
            "https://chatgpt.com/g/g-p-6a412e0893948191a5dea968f713806e/project"
        )

        self.path_data_zip = Path(
            r"datas\data_zip\upload.zip"
        )

        self.path_prompt_file = Path(
            r"datas\prompts\prompt.txt"
        )

        self.path_result_file = Path(
            r"datas\result_analyse\result_gpt.json"
        )

    @staticmethod
    def validate_file(file_path: Path) -> Path:
        """
        ตรวจสอบว่าไฟล์มีอยู่จริง และคืนค่า absolute path
        """
        resolved_path = file_path.resolve()

        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"File not found: {resolved_path}"
            )

        return resolved_path

    def read_file_prompt(
        self,
        file_path: Optional[Path] = None,
    ) -> str:
        """
        อ่านข้อความ prompt จากไฟล์
        """
        prompt_path = self.validate_file(
            file_path or self.path_prompt_file
        )

        prompt_text = prompt_path.read_text(
            encoding="utf-8"
        ).strip()

        if not prompt_text:
            raise ValueError(
                f"Prompt file is empty: {prompt_path}"
            )

        return prompt_text

    def save_result_to_file(
        self,
        result: str,
        file_path: Optional[Path] = None,
    ) -> None:
        """
        ตรวจสอบ JSON และบันทึกลงไฟล์
        """
        output_path = (
            file_path or self.path_result_file
        ).resolve()

        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError as error:
            invalid_result_path = output_path.with_suffix(
                ".invalid.txt"
            )

            invalid_result_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            invalid_result_path.write_text(
                result,
                encoding="utf-8",
            )

            raise ValueError(
                "GPT response is not valid JSON. "
                f"Raw response saved at: {invalid_result_path}"
            ) from error

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                parsed_result,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # print_log(f"Result saved: {output_path}")

    def wait_for_response_finished(self) -> None:
        """
        รอให้ ChatGPT เริ่มสร้างคำตอบและสร้างคำตอบเสร็จ
        """
        stop_button = self.page.get_by_test_id(
            "stop-button"
        )

        send_button = self.page.get_by_test_id(
            "send-button"
        )

        # รอให้ปุ่ม Stop ปรากฏ แสดงว่าเริ่มสร้างคำตอบแล้ว
        try:
            stop_button.wait_for(
                state="visible",
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            # คำตอบอาจเสร็จเร็วมากจนไม่ทันพบปุ่ม Stop
            print_log(
                "Stop button was not detected. "
                "Waiting for send button instead."
            )

        stop_button.wait_for(
            state="hidden",
            timeout=300_000,
        )


    def get_result(self) -> str:
        """
        อ่าน JSON จาก code block ของคำตอบ
        """
        result_locator = self.page.locator(
            "#code-block-viewer pre"
        ).last

        result_locator.wait_for(
            state="visible",
            timeout=60_000,
        )

        result = result_locator.inner_text().strip()

        if not result:
            raise ValueError(
                "GPT returned an empty code block"
            )

        return result

    def delete_chat_history(self) -> None:
        more_options = self.page.get_by_test_id("conversation-options-button")
        more_options.wait_for(state="attached")
        more_options.click()

        delete_button = self.page.get_by_test_id("delete-chat-menu-item")
        delete_button.wait_for(state="attached")
        delete_button.click()


        confirm_delete_button = self.page.get_by_test_id("delete-conversation-confirm-button")
        confirm_delete_button.wait_for(state="attached")
        confirm_delete_button.click()

    def analyze(
        self,
        file_path: Optional[Path] = None,
    ) -> dict:
        """
        อัปโหลดไฟล์ ส่ง prompt รอผลลัพธ์ และบันทึก JSON
        """
        data_zip_path = self.validate_file(
            file_path or self.path_data_zip
        )

        prompt_text = self.read_file_prompt()

        print_log(f"Opening GPT project: {self.url_gpt_project}")


        self.page.goto(
            self.url_gpt_project,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        prompt_editor = self.page.locator(
            "#prompt-textarea"
        )

        upload_input = self.page.locator(
            "#upload-files"
        )

        send_button = self.page.get_by_test_id(
            "send-button"
        )



        prompt_editor.wait_for(
            state="attached",
            timeout=60_000,
        )

        upload_input.wait_for(
            state="attached",
            timeout=60_000,
        )

        print_log(f"Uploading file: {data_zip_path}")

        upload_input.set_input_files(
            str(data_zip_path)
        )
        # wait progress upload file
        self.page.locator("button.cursor-wait").wait_for( state="detached", timeout=30_000)

        print_log("Filling prompt")


        prompt_editor.fill(prompt_text)

        expect(send_button).to_be_visible(
            timeout=60_000
        )

        expect(send_button).to_be_enabled(
            timeout=60_000
        )

        print_log("Sending prompt")

        old_url = self.page.url

        send_button.click()

        self.page.wait_for_url(
            lambda url: str(url) != old_url,
            timeout=30_000,
        )


        self.page.reload(wait_until="load")

        print_log("Waiting for GPT response")

        self.wait_for_response_finished()

        result = self.get_result()

        # ตรวจสอบและบันทึกผลลัพธ์
        self.save_result_to_file(result)

        parsed_result = json.loads(result)

        self.delete_chat_history()

        print_log("Analysis completed successfully")

        return parsed_result

    def run(self) -> dict:
        """
        เริ่มกระบวนการวิเคราะห์
        """
        try:
            return self.analyze()

        except PlaywrightTimeoutError as error:
            print_log(f"Playwright timeout: {error}")
            raise

        except FileNotFoundError as error:
            print_log(f"File error: {error}")
            raise

        except ValueError as error:
            print_log(f"Invalid result: {error}")
            raise

        except Exception as error:
            print_log(f"Error during analysis: {error}")
            raise


def gpt_runner() -> None:

    try:
        with sync_playwright() as playwright:
            analyzer = GptAnalyzer(playwright)
            result = analyzer.run()

            # print_log("GPT result:")
            # print_log(
            #     json.dumps(
            #         result,
            #         ensure_ascii=False,
            #         indent=2,
            #     )
            # )

    except Exception as error:
        print_log(f"Fatal error: {error}")
        raise SystemExit(1)



if __name__ == "__main__":
    gpt_runner()
