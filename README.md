////////////////////////////////////
ติดตั้ง python
////////////////////////////////////
Python 3.10+ แนะนำ

////////////////////////////////////
ติดตั้ง package สำหรับ การจำลองการกด
////////////////////////////////////
pip install pyautogui pyperclip

////////////////////////////////////
วิธีนำไปใช้งาน
////////////////////////////////////

from chatgpt_analyse import ChatGPTUploaderConfig, ChatGPTUploader

def main():
/// process ก่อนหน้า

    cfg = ChatGPTUploaderConfig(

        # โฟลเดอร์ไฟล์ที่จะต้องการupload ให้ gpt
        data_folder=Path(r"C:/..../data_files"),

        # โฟลเดอร์เอาไว้เก็บผล
        output_folder=Path(r"C:/..../result_analyse"),

        # โฟลเดอร์ดาวน์โหลดของ Browser
        download_folder=Path(r"C:/....../Downloads"),

        # ไฟล์ prompt (ถ้าอยู่ root เดียวกับ prompt.txt ใช้แบบนี้ได้)
        prompt_path=Path("prompt.txt"),

        # ชื่อไฟล์ผลลัพธ์ปลายทางที่ต้องการ
        result_file=Path("result_gpt.json"),
    )

    bot = ChatGPTUploader(cfg)
    bot.run_all()

    /// process ถัดไป
