from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5

from modules.utils.custom_print import print_log


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_FOLDER = PROJECT_ROOT / "datas" / "result_analyse"
DEFAULT_RESULT_FILE = "result_gpt.json"


def load_signal(
    file_name: str = DEFAULT_RESULT_FILE,
) -> dict[str, Any]:
    """โหลดผลลัพธ์ JSON จาก datas/result_analyse."""
    signal_path = RESULT_FOLDER / file_name

    if not signal_path.is_file():
        raise FileNotFoundError(
            f"Signal file not found: {signal_path}"
        )

    try:
        with signal_path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            signal = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in signal file: {error}"
        ) from error
    except OSError as error:
        raise RuntimeError(
            f"Failed to read signal file: {error}"
        ) from error

    if not isinstance(signal, dict):
        raise ValueError("Signal JSON must be an object")

    print_log(f"Load signal success: {signal_path}")
    return signal


def _parse_ticket(value: Any, index: int) -> int:
    field_name = f"modify.close_pending[{index}]"

    if isinstance(value, bool):
        raise ValueError(
            f"'{field_name}' must be a positive integer"
        )

    if isinstance(value, int):
        ticket = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(
                f"'{field_name}' must be a positive integer"
            )
        ticket = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        ticket = int(value.strip())
    else:
        raise ValueError(
            f"'{field_name}' must be a positive integer"
        )

    if ticket <= 0:
        raise ValueError(
            f"'{field_name}' must be greater than zero"
        )

    return ticket


def get_close_pending_tickets(
    signal: dict[str, Any],
) -> list[int]:
    """อ่านเฉพาะ signal['modify']['close_pending']."""
    modify = signal.get("modify")

    if modify is None:
        return []

    if not isinstance(modify, dict):
        raise ValueError("'modify' must be an object")

    close_pending = modify.get("close_pending", [])

    if close_pending is None:
        return []

    if not isinstance(close_pending, list):
        raise ValueError(
            "'modify.close_pending' must be a list"
        )

    tickets: list[int] = []
    seen: set[int] = set()

    for index, value in enumerate(close_pending):
        ticket = _parse_ticket(value, index)

        if ticket not in seen:
            tickets.append(ticket)
            seen.add(ticket)

    return tickets


def _get_active_pending_order(
    ticket: int,
    mt5_client: Any,
) -> Any | None:
    orders = mt5_client.orders_get(ticket=ticket)

    if orders is None:
        raise RuntimeError(
            f"Failed to get pending order {ticket}: "
            f"{mt5_client.last_error()}"
        )

    if not orders:
        print_log(
            f"Pending order {ticket} is not active. Skip."
        )
        return None

    order = orders[0]

    pending_types = {
        mt5_client.ORDER_TYPE_BUY_LIMIT,
        mt5_client.ORDER_TYPE_SELL_LIMIT,
        mt5_client.ORDER_TYPE_BUY_STOP,
        mt5_client.ORDER_TYPE_SELL_STOP,
    }

    buy_stop_limit = getattr(
        mt5_client,
        "ORDER_TYPE_BUY_STOP_LIMIT",
        None,
    )
    sell_stop_limit = getattr(
        mt5_client,
        "ORDER_TYPE_SELL_STOP_LIMIT",
        None,
    )

    if buy_stop_limit is not None:
        pending_types.add(buy_stop_limit)

    if sell_stop_limit is not None:
        pending_types.add(sell_stop_limit)

    if order.type not in pending_types:
        raise ValueError(
            f"Ticket {ticket} is not a pending order"
        )

    return order


def _build_remove_request(
    ticket: int,
    mt5_client: Any,
) -> dict[str, Any]:
    return {
        "action": mt5_client.TRADE_ACTION_REMOVE,
        "order": ticket,
        "comment": "gpt close pending",
    }


def _check_remove_request(
    request: dict[str, Any],
    mt5_client: Any,
) -> Any:
    result = mt5_client.order_check(request)

    if result is None:
        raise RuntimeError(
            "order_check returned None: "
            f"{mt5_client.last_error()}"
        )

    if result.retcode != 0:
        raise RuntimeError(
            "Close pending check failed: "
            f"retcode={result.retcode}, "
            f"comment={result.comment}"
        )

    return result


def _send_remove_request(
    request: dict[str, Any],
    mt5_client: Any,
) -> Any:
    result = mt5_client.order_send(request)

    if result is None:
        raise RuntimeError(
            "order_send returned None: "
            f"{mt5_client.last_error()}"
        )

    success_codes = {
        mt5_client.TRADE_RETCODE_DONE,
        mt5_client.TRADE_RETCODE_PLACED,
    }

    done_partial = getattr(
        mt5_client,
        "TRADE_RETCODE_DONE_PARTIAL",
        None,
    )

    if done_partial is not None:
        success_codes.add(done_partial)

    if result.retcode not in success_codes:
        raise RuntimeError(
            "Close pending failed: "
            f"retcode={result.retcode}, "
            f"comment={result.comment}"
        )

    return result


def close_pending_order(
    ticket: int,
    dry_run: bool = True,
    mt5_client: Any = mt5,
) -> Any | None:
    """ตรวจและยกเลิก Pending Order หนึ่ง ticket."""
    order = _get_active_pending_order(
        ticket=ticket,
        mt5_client=mt5_client,
    )

    if order is None:
        return None

    request = _build_remove_request(
        ticket=ticket,
        mt5_client=mt5_client,
    )

    print_log(
        f"Close pending | symbol: {order.symbol}, "
        f"ticket: {ticket}"
    )

    _check_remove_request(
        request=request,
        mt5_client=mt5_client,
    )

    if dry_run:
        print_log(
            f"DRY RUN: pending order {ticket} "
            "was checked but not removed."
        )
        return None

    result = _send_remove_request(
        request=request,
        mt5_client=mt5_client,
    )

    print_log(
        f"Pending order {ticket} removed successfully"
    )
    return result


def run_close_pending(
    file_name: str = DEFAULT_RESULT_FILE,
    dry_run: bool = True,
    mt5_client: Any = mt5,
) -> bool:
    """
    โหลดผลลัพธ์ อ่านเฉพาะ modify.close_pending และปิด Pending Order.

    Returns:
        False: ไม่มี ticket ใน modify.close_pending
        True: พบ ticket และประมวลผลแล้ว
    """
    signal = load_signal(file_name=file_name)
    tickets = get_close_pending_tickets(signal)

    if not tickets:
        print_log("modify.close_pending is empty.")
        return False

    if not mt5_client.initialize():
        raise RuntimeError(
            f"MT5 initialize failed: {mt5_client.last_error()}"
        )

    try:
        for ticket in tickets:
            close_pending_order(
                ticket=ticket,
                dry_run=dry_run,
                mt5_client=mt5_client,
            )
    finally:
        mt5_client.shutdown()

    print_log("close_pending completed.")
    return True


if __name__ == "__main__":
    run_close_pending(
        file_name="result_gpt.json",

        # True = ตรวจสอบอย่างเดียว ไม่ลบจริง
        # False = ส่งคำสั่งลบ Pending Order จริง
        dry_run=False,
    )
