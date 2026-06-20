import MetaTrader5 as mt5
import json
from pathlib import Path


def get_orders_by_symbol(symbol: str = None, output_folder: Path = None):

    try:
        if not mt5.initialize():
            print("initialize() failed:", mt5.last_error())
            return

        orders = mt5.orders_get(symbol=symbol)

        # แปลง orders เป็น list ของ dict
        if orders:
            data = [p._asdict() for p in orders]
            # print(f"Total orders on {symbol} =", len(data))
        else:
            # print(f"No open orders on {symbol}")
            data = []   # ไม่มี position ก็เป็น array ว่าง

        # กำหนด path
        if output_folder:
            output_folder.mkdir(parents=True, exist_ok=True)
            # file_path = output_folder / f"{symbol}_orders.json"
            file_path = output_folder / "orders.json"
        else:
            # file_path = Path(f"{symbol}_orders.json")
            file_path = Path("orders.json")

        # save json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # print(f"JSON saved -> {file_path}")

    except Exception as e:
        print(e)

    finally:
        mt5.shutdown()

if __name__ == "__main__":
    get_orders_by_symbol("XAUUSDc", Path("./data_files"))