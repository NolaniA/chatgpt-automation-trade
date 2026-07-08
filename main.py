from __future__ import annotations

import argparse
from typing import Any

import MetaTrader5 as mt5

from modules.python_package.install_package import package_runner
from modules.setup_browser.edge_profile import (
    kill_edge_processes,
    setup_edge_profile,
)
from modules.chatgpts.workflow_analyse import gpt_runner

from modules.metatrader5.mt5_initialize import initialize_mt5
from modules.metatrader5.account_info import get_account_info
from modules.metatrader5.current_price import get_current_price
from modules.metatrader5.orders_get import get_orders_by_symbol
from modules.metatrader5.positions_get import get_positions_by_symbol
from modules.metatrader5.history_get import get_deal_history_by_symbol
from modules.metatrader5.fetch_ohlcv import MT5Config, MT5DataFeed
from modules.metatrader5.send_order import MT5AutoTrader

from modules.utils.merge_to_zip import create_zip_file
from modules.utils.check_market import is_market_open
from modules.utils.interval_time import wait_until_next_round

from modules.utils.custom_print import print_log



DEFAULT_TIMEFRAMES = [
    mt5.TIMEFRAME_M1,
    mt5.TIMEFRAME_M5,
    mt5.TIMEFRAME_M15,
    mt5.TIMEFRAME_M30,
    mt5.TIMEFRAME_H1,
    mt5.TIMEFRAME_H4,
    mt5.TIMEFRAME_D1,
]

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


def parse_timeframes(value: str) -> list[int]:
    """
    ตัวอย่าง input:
        M1,M5,M15,H1,H4,D1
    """
    if not isinstance(value, str) or not value.strip():
        raise argparse.ArgumentTypeError(
            "multi_tf must not be empty"
        )

    timeframe_names = [
        item.strip().upper()
        for item in value.split(",")
        if item.strip()
    ]

    if not timeframe_names:
        raise argparse.ArgumentTypeError(
            "No valid timeframes provided"
        )

    invalid_timeframes = [
        name
        for name in timeframe_names
        if name not in TIMEFRAME_MAP
    ]

    if invalid_timeframes:
        available = ", ".join(TIMEFRAME_MAP.keys())

        raise argparse.ArgumentTypeError(
            f"Invalid timeframe: {', '.join(invalid_timeframes)}. "
            f"Available: {available}"
        )

    return [
        TIMEFRAME_MAP[name]
        for name in timeframe_names
    ]


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"'{value}' must be an integer"
        ) from error

    if number <= 0:
        raise argparse.ArgumentTypeError(
            f"'{value}' must be greater than 0"
        )

    return number


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MetaTrader 5 ChatGPT automation trader"
    )

    parser.add_argument(
        "--multi_symbol",
        "--multi-symbol",
        dest="multi_symbol",
        type=str,
        required=False,
        default=None,
        help="Comma-separated symbols, example: XAUUSDc,BTCUSDc",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        required=False,
        default="XAUUSDc",
        help="Single symbol, default: XAUUSDc",
    )

    parser.add_argument(
        "--multi_tf",
        "--multi-tf",
        dest="multi_tf",
        type=parse_timeframes,
        default=DEFAULT_TIMEFRAMES,
        help=(
            "Comma-separated timeframes, "
            "example: M1,M5,M15,H1,H4,D1"
        ),
    )

    parser.add_argument(
        "--bars",
        type=positive_int,
        default=100,
        help="Number of OHLCV bars, default: 100",
    )

    parser.add_argument(
        "--interval_minute",
        "--interval-minute",
        dest="interval_minute",
        type=positive_int,
        default=15,
        help="Cycle interval in minutes, default: 15",
    )

    parser.add_argument(
        "--dry_run",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Check the order without sending it",
    )

    return parser


def resolve_symbols(
    symbol: str,
    multi_symbol: str | None,
) -> list[str]:
    raw_symbols = multi_symbol if multi_symbol else symbol

    symbols = [
        item.strip()
        for item in raw_symbols.split(",")
        if item.strip()
    ]

    if not symbols:
        raise ValueError("At least one symbol is required")

    # ลบ symbol ซ้ำ แต่รักษาลำดับเดิม
    return list(dict.fromkeys(symbols))


def shutdown_mt5_client(mt5_client: Any) -> None:
    if mt5_client is None:
        return

    shutdown = getattr(mt5_client, "shutdown", None)

    if callable(shutdown):
        shutdown()


def collect_mt5_data(
    symbol: str,
    bars: int,
    timeframes: list[int],
) -> None:
    mt5_client = None

    try:
        mt5_client = initialize_mt5()

        if mt5_client is None:
            raise RuntimeError(
                "initialize_mt5() returned None"
            )

        get_account_info(
            mt5_client=mt5_client,
        )

        get_current_price(
            symbol=symbol,
            mt5_client=mt5_client,
        )

        get_orders_by_symbol(
            symbol=symbol,
            mt5_client=mt5_client,
        )

        get_positions_by_symbol(
            symbol=symbol,
            mt5_client=mt5_client,
        )

        get_deal_history_by_symbol(
            symbol=symbol,
            mt5_client=mt5_client,
        )

        config = MT5Config(
            symbol=symbol,
            bars=bars,
            timeframes=timeframes,
        )

        MT5DataFeed(config).run_all()

    finally:
        shutdown_mt5_client(mt5_client)


def run_cycle(
    symbol: str,
    bars: int,
    timeframes: list[int],
    dry_run: bool,
) -> bool:
    print_log("=" * 60)
    print_log(f"Starting cycle for symbol: {symbol}")
    print_log("=" * 60)

    try:
        # 1. ดึงข้อมูล MT5 และบันทึกเป็น JSON
        collect_mt5_data(
            symbol=symbol,
            bars=bars,
            timeframes=timeframes,
        )

        # 2. รวม JSON เป็น ZIP
        zip_path = create_zip_file()
        print_log(f"ZIP created: {zip_path}")

        # 3. เปิด Edge profile และส่งข้อมูลให้ ChatGPT
        # setup_edge_profile()

        gpt_runner()

        # 4. อ่านผลวิเคราะห์และส่งคำสั่งเทรด
        trader = MT5AutoTrader(
            symbol=symbol,
            file_name="result_gpt.json",
            risk_percent=2.0,
            dry_run=dry_run,
        )

        result = trader.run()

        if result is None:
            print_log(
                f"Cycle completed without an order: {symbol}"
            )
        else:
            print_log(
                f"Cycle completed with an order: {symbol}"
            )

        return True

    except Exception as error:
        print_log(
            f"Cycle failed for '{symbol}': "
            f"{type(error).__name__}: {error}"
        )

        return False

    # finally:
    #     kill_edge_processes()


def main() -> None:
    package_runner()

    parser = create_parser()
    args = parser.parse_args()

    symbols = resolve_symbols(
        symbol=args.symbol,
        multi_symbol=args.multi_symbol,
    )

    print_log(f"Symbols: {symbols}", end="\n")
    print_log(f"Bars: {args.bars}", end="\n")
    print_log(f"Timeframes: {args.multi_tf}", end="\n")
    print_log(f"Interval: {args.interval_minute} minutes", end="\n")
    print_log(f"Dry run: {args.dry_run}", end="\n")


    try:
        while True:
            for symbol in symbols:
                try:
                    market_open = is_market_open(
                        symbol=symbol,
                    )
                except Exception as error:
                    print_log(
                        f"Failed to check market for "
                        f"'{symbol}': {error}"
                    )
                    continue

                if not market_open:
                    print_log(
                        f"Market is closed for: {symbol}"
                    )
                    continue
                try:
                    run_cycle(
                        symbol=symbol,
                        bars=args.bars,
                        timeframes=args.multi_tf,
                        dry_run=args.dry_run,
                    )
                except Exception as e:
                    print_log(f"cycle analyse fail: {e}")
                # finally:
                #     kill_edge_processes()


            wait_until_next_round(
                minute_round=args.interval_minute,
            )

    except KeyboardInterrupt:
        print_log("\nProgram stopped by user.")

    # finally:
    #     kill_edge_processes()
        # mt5.shutdown()


if __name__ == "__main__":
    main()