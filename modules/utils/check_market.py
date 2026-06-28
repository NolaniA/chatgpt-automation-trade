from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
from modules.utils.custom_print import print_log




def wait_market_open(symbol: str):
    print_log(f"symbol : {symbol}")

    if "BTC" in symbol.upper() or "ETH" in symbol.upper():
        print_log("Crypto market 24/7 — no wait")
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
        print_log(f"Market closed. Waiting {int(wait_seconds)} seconds")
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

        print_log(f"Wait 6 am : {int(wait_seconds)} sec")
        time.sleep(wait_seconds)


def is_market_open(symbol: str, time_open: int = 6, time_close: int = 3) -> bool:

    if "BTC" in symbol.upper() or "ETH" in symbol.upper():
        return True

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    weekday = now.weekday()

    # forex / gold close weekend
    if weekday in (5, 6):
        return False

    # before 6:00
    if now.hour < time_open and now.hour > time_close:
        return False

    return True
