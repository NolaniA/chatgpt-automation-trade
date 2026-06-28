import MetaTrader5 as mt5


def initialize_mt5() -> mt5:
    if not mt5.initialize():
        raise RuntimeError(f"initialize() failed, error code: {mt5.last_error()}")

    return mt5