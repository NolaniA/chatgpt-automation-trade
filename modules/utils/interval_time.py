from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
from modules.utils.custom_print import print_log


def wait_until_next_round(minute_round: int):
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    minute = (now.minute // minute_round + 1) * minute_round
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
    print_log(f"Waiting {int(wait_seconds)} seconds...", end="\n")
    time.sleep(wait_seconds)