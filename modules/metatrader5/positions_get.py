import MetaTrader5 as mt5
import json
from pathlib import Path


def get_positions_by_symbol(symbol: str = None, output_folder: Path = None):

    try:
        if not mt5.initialize():
            print("initialize() failed:", mt5.last_error())
            return

        positions = mt5.positions_get(symbol=symbol)

        # แปลง positions เป็น list ของ dict
        if positions:
            data = [p._asdict() for p in positions]
            # print(f"Total positions on {symbol} =", len(data))
        else:
            # print(f"No open positions on {symbol}")
            data = []   # ไม่มี position ก็เป็น array ว่าง

        # กำหนด path
        if output_folder:
            output_folder.mkdir(parents=True, exist_ok=True)
            # file_path = output_folder / f"{symbol}_positions.json"
            file_path = output_folder / "positions.json"
        else:
            # file_path = Path(f"{symbol}_positions.json")
            file_path = Path("positions.json")

        # save json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # print(f"JSON saved -> {file_path}")

    except Exception as e:
        print(e)

    finally:
        mt5.shutdown()

if __name__ == "__main__":
    get_positions_by_symbol("XAUUSDc", Path("data_files"))