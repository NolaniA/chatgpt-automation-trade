import MetaTrader5 as mt5
import json
from pathlib import Path



def get_current_price(symbol: str, output_folder: Path):

    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize
        if not mt5.initialize():
            raise RuntimeError(f"initialize() failed, error code: {mt5.last_error()}")

        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select symbol {symbol}, error code = {mt5.last_error()}")
            mt5.shutdown()
            quit()

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            print(f"Failed to get tick data for {symbol}, error code = {mt5.last_error()}")


        # ----------------------------
        # Convert to dict
        # ----------------------------
        tick_info = tick._asdict()

        # Save JSON
        json_path = output_folder / "current_price.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tick_info, f, indent=4)

        mt5.shutdown()



        return tick_info

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    get_current_price()
