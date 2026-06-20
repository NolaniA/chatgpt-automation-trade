import time
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import os
from dotenv import load_dotenv
from pathlib import Path
from zoneinfo import ZoneInfo


load_dotenv()


from modules.chatgpts.chatgpt_analyse import ChatGPTUploaderConfig, ChatGPTUploader
from modules.metatrader5.fetch_ohlcv import MT5Config, MT5DataFeed
from modules.metatrader5.account_info import get_account_info
from modules.metatrader5.send_order import MT5AutoTrader
from modules.metatrader5.current_price import get_current_price
from modules.metatrader5.orders_get import get_orders_by_symbol
from modules.metatrader5.positions_get import get_positions_by_symbol


# SYMBOLS = str(os.getenv("SYMBOL"))
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "").split(",")]
BARS = int(os.getenv("BAR"))
SAVE_FOLDER = Path(os.getenv("DATA_FOLDER", "./data_files"))
URL_GPT_PROJECT = os.getenv("URL_GPT_PROJECT")
OUTPUT_FOLDER = Path(os.getenv("OUTPUT_FOLDER"))
DOWNLOAD_FOLDER = Path(os.getenv("DOWNLOAD_FOLDER"))
DATA_FOLDER = Path(os.getenv("DATA_FOLDER"))
PROMPT_PATH = Path(os.getenv("PROMPT_PATH"))
SIGNAL_FOLDER = Path(os.getenv("SIGNAL_PATH"))
MONUTE_ROUND = int(os.getenv("MONUTE_ROUND"))


def wait_market_open(symbol: str):
    print(f"symbol : {symbol}")

    if "BTC" in symbol.upper() or "ETH" in symbol.upper():
        print("Crypto market 24/7 — no wait")
        return

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    weekday = now.weekday()

    # check weekend
    if weekday in (5, 6) and "BTC" not in symbol.upper():

        day = 2 if weekday == 5 else 1
        next_run = (now + timedelta(days=day)).replace(
            hour=6, minute=0, second=0, microsecond=0
        )

        wait_seconds = (next_run - now).total_seconds()
        print(f"Market closed. Waiting {int(wait_seconds)} seconds")
        time.sleep(wait_seconds)

    # wait 6 am
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    close = (6 - int(now.strftime('%H'))) > 2

    if  not close :
        return

    target = now.replace(hour=6, minute=0, second=0, microsecond=0)

    if now >= target:
        target = target + timedelta(days=1)

        wait_seconds = (target - now).total_seconds()

        print(f"Wait 6 am : {int(wait_seconds)} sec")
        time.sleep(wait_seconds)

def is_market_open(symbol: str):

    if "BTC" in symbol.upper() or "ETH" in symbol.upper():
        return True

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    weekday = now.weekday()

    # forex / gold close weekend
    if weekday in (5, 6):
        return False

    # before 6:00
    if now.hour < 6 and now.hour > 3:
        return False

    return True


def wait_until_next_round():
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    minute = (now.minute // MONUTE_ROUND + 1) * MONUTE_ROUND
    if minute == 60:
        # next_run = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        next_run = (now + timedelta(hours=1)).replace(
            minute=0,
            second=0,
            microsecond=0
        )
    else:
        next_run = now.replace(minute=minute, second=0, microsecond=0)

    wait_seconds = (next_run - now).total_seconds()
    print(f"Waiting {int(wait_seconds)} seconds...")
    time.sleep(wait_seconds)


def run_cycle(symbol: str):
    print("=== RUN START ===", datetime.now())



    config = MT5Config(
        symbol=symbol,
        timeframes=[
            mt5.TIMEFRAME_M1,
            mt5.TIMEFRAME_M15,
            mt5.TIMEFRAME_H1,
        ],
        bars=BARS,
        save_folder=SAVE_FOLDER
    )

    feed = MT5DataFeed(config)
    feed.run_all()

    get_account_info(output_folder=DATA_FOLDER)
    get_current_price(symbol=symbol, output_folder=DATA_FOLDER)
    get_orders_by_symbol(symbol=symbol, output_folder=DATA_FOLDER)
    get_positions_by_symbol(symbol=symbol, output_folder=DATA_FOLDER)




    cfg = ChatGPTUploaderConfig(
        url_gpt_project=URL_GPT_PROJECT,
        data_folder=DATA_FOLDER,
        output_folder=OUTPUT_FOLDER,
        download_folder=DOWNLOAD_FOLDER,
        prompt_path=PROMPT_PATH,

    )
    bot = ChatGPTUploader(cfg)
    bot.run_all()



    trader = MT5AutoTrader(
        symbol=symbol,
        signal_path=SIGNAL_FOLDER
        )
    trader.run()

    print("=== RUN END ===", datetime.now())


if __name__ == "__main__":
    while True:
        # wait_market_open(symbol=)
        for symbol in SYMBOLS:
            if not is_market_open(symbol=symbol):
                continue
            run_cycle(symbol=symbol)
        wait_until_next_round()
