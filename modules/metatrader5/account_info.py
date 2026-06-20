import MetaTrader5 as mt5
import pandas as pd
import json
from pathlib import Path


def get_account_info(
    output_folder: Path = None
    # output_folder: Path = Path(r"C:/Users/Saeng/Documents/GitHub/chatgpt-analyse/data_files")
):

    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize
        if not mt5.initialize():
            raise RuntimeError(f"initialize() failed, error code: {mt5.last_error()}")

        account_info = mt5.account_info()

        if account_info is None:
            raise RuntimeError(f"Failed to get account info, error code: {mt5.last_error()}")

        # print("=== Account Information ===")
        # print(f"Login: {account_info.login}")
        # print(f"Name: {account_info.name}")
        # print(f"Server: {account_info.server}")
        # print(f"Balance: {account_info.balance}")
        # print(f"Equity: {account_info.equity}")

        # ----------------------------
        # Convert to dict
        # ----------------------------
        account_dict = account_info._asdict()

        # Save CSV
        # df = pd.DataFrame([account_dict])
        # csv_path = output_folder / "account_info.csv"
        # df.to_csv(csv_path, index=False)

        # Save JSON
        json_path = output_folder / "account_info.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(account_dict, f, indent=4)

        # print(f"\nSaved CSV: {csv_path}")
        # print(f"Saved JSON: {json_path}")

        return account_dict

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    get_account_info()