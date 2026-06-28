
from typing import Any

import MetaTrader5 as mt5
from modules.utils.save_json_to_data_files import save_json
from modules.utils.custom_print import print_log



def get_current_price(
    symbol: str,
    file_name: str = "current_price.json",
    mt5_client: Any = mt5,
) -> dict[str, Any]:
    if not symbol or not symbol.strip():
        raise ValueError("symbol must not be empty")

    symbol = symbol.strip()

    if not mt5_client.symbol_select(symbol, True):
        raise RuntimeError(
            f"Failed to select symbol '{symbol}': {mt5_client.last_error()}"
        )

    tick = mt5_client.symbol_info_tick(symbol)

    if tick is None:
        raise RuntimeError(
            f"Failed to get tick data for '{symbol}': "
            f"{mt5_client.last_error()}"
        )

    tick_info = tick._asdict()
    save_json(file_name, tick_info)
    return tick_info



if __name__ == "__main__":
    try:
        if not mt5.initialize():
            raise RuntimeError(
                f"Failed to initialize MetaTrader 5: {mt5.last_error()}"
            )

        current_price = get_current_price(
            symbol="XAUUSDc",
        )

        print_log(current_price)

    finally:
        mt5.shutdown()