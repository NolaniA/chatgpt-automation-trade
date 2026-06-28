from typing import Any

import MetaTrader5 as mt5

from modules.utils.save_json_to_data_files import save_json
from modules.utils.custom_print import print_log



def get_account_info(
    file_name: str = "account_info.json",
    mt5_client: Any = mt5,
) -> dict:
    account_info = mt5_client.account_info()

    if account_info is None:
        raise RuntimeError(
            f"Failed to get account info: {mt5_client.last_error()}"
        )

    account_dict = account_info._asdict()
    save_json(file_name, account_dict)

    return account_dict


if __name__ == "__main__":
    try:
        if not mt5.initialize():
            raise RuntimeError(
                f"Failed to initialize MetaTrader 5: {mt5.last_error()}"
            )

        get_account_info()

    finally:
        mt5.shutdown()