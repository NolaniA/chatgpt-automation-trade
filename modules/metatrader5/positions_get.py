
import MetaTrader5 as mt5
from modules.utils.save_json_to_data_files import save_json
from typing import Any


def get_positions_by_symbol(
        symbol: str,
        mt5_client: Any = mt5,
        file_name: str = "positions.json"
        ):

        positions = mt5_client.positions_get(symbol=symbol)

        if positions:
            data = [p._asdict() for p in positions]
        else:
            data = []

        save_json(file_name=file_name,data=data)



if __name__ == "__main__":
    try:
        if not mt5.initialize():
            raise RuntimeError(
                f"Failed to initialize MetaTrader 5: {mt5.last_error()}"
            )

        positions = get_positions_by_symbol(
            symbol="XAUUSDc", mt5_client=mt5
        )

        print_log(positions)

    finally:
        mt5.shutdown()