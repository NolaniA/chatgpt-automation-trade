from modules.package_setup.install_package import pip_install_package
from modules.setup_browser.edge_setup_profile import setup_edge_profile

from pathlib import Path
from playwright.sync_api import sync_playwright


if __name__ == "__main__":
    print("=== SETUP START ===")

    # 1. Install packages
    if pip_install_package("requirements.txt"):
        print("Packages installed successfully.")
    else:
        print("Failed to install packages.")

    # 2. Setup Edge profile for Playwright
    setup_edge_profile()

    print("=== SETUP END ===")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        url_gpt_project = "https://chatgpt.com/g/g-p-6a26d2dd360c8191a7f679ced3858d9d-investor/project"

        page.goto(url_gpt_project, wait_until="domcontentloaded")

        # ช่องพิมพ์ prompt
        composer = page.locator("p[data-placeholder]").last
        composer.wait_for(state="visible", timeout=30000)
        composer.click()

        # ล้างข้อความเดิม ถ้ามี
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")

        # upload file
        file_path = Path(r"datas\data_zip\data.zip").resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # กดปุ่ม attach/upload
        with page.expect_file_chooser() as fc_info:
            page.locator('button[aria-label*="Attach"], button[aria-label*="Upload"], button:has-text("Attach")').first.click()

        file_chooser = fc_info.value
        file_chooser.set_files(str(file_path))

        # รอ upload สักหน่อย
        page.wait_for_timeout(3000)

        # พิมพ์ prompt
        composer.click()
        page.keyboard.type("/")

        # หรือใส่ prompt เต็ม
        # page.keyboard.type("วิเคราะห์ไฟล์นี้ให้หน่อย")

        # กดส่ง
        # page.locator('button[data-testid="send-button"]').click()

        page.pause()