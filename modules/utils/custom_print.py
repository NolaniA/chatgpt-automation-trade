import builtins
from typing import Any


def print_status(message: str) -> None:
    builtins.print(
        f"{message:<100}",
        end="\r",
        flush=True,
    )


# def print_log(message: str, end: str = "\r") -> None:
#     builtins.print(message, end=end, flush=True)



def print_log(
    message: Any,
    end: str = "\r",
) -> None:
    builtins.print(
        f"\r\033[2K{message}",
        end=end,
        flush=True,
    )