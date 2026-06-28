from datetime import datetime, timedelta, timezone
from typing import Any

import MetaTrader5 as mt5

from modules.utils.save_json_to_data_files import save_json


def get_deal_history_by_symbol(
    symbol: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    file_name: str = "deal_history.json",
    mt5_client: Any = mt5,
) -> list[dict[str, Any]]:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")

    symbol = symbol.strip()

    # Default date_to คือเวลาปัจจุบัน
    if date_to is None:
        date_to = datetime.now(timezone.utc)

    # Default date_from คือย้อนหลัง 7 วันจาก date_to
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    if date_from >= date_to:
        raise ValueError(
            f"date_from ({date_from}) must be earlier than "
            f"date_to ({date_to})"
        )

    history = mt5_client.history_deals_get(
        date_from,
        date_to,
        group=symbol,
    )

    if history is None:
        raise RuntimeError(
            f"Failed to get deal history for '{symbol}': "
            f"{mt5_client.last_error()}"
        )

    data = [
        deal._asdict()
        for deal in history
        if deal.symbol == symbol
    ]

    saved = save_json(
        file_name=file_name,
        data=data,
    )

    if not saved:
        raise RuntimeError(
            f"Failed to save deal history to '{file_name}'"
        )

    return data


def main() -> None:
    initialized = False

    try:
        if not mt5.initialize():
            raise RuntimeError(
                f"Failed to initialize MetaTrader 5: "
                f"{mt5.last_error()}"
            )

        initialized = True

        # ไม่ส่ง date_from และ date_to
        # ระบบจะดึงประวัติย้อนหลัง 7 วันอัตโนมัติ
        history = get_deal_history_by_symbol(
            symbol="XAUUSDc",
            file_name="deal_history.json",
            mt5_client=mt5,
        )

        print_log(f"Found {len(history)} deals")

        for deal in history:
            print_log(deal)

    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    main()