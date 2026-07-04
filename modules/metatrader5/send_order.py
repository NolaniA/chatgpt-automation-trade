from __future__ import annotations

import json
import math
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any
from modules.utils.custom_print import print_log


import MetaTrader5 as mt5


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_FOLDER = PROJECT_ROOT / "datas" / "result_analyse"


class MT5AutoTrader:

    def __init__(
        self,
        symbol: str,
        file_name: str = "result_gpt.json",
        risk_percent: float = 2.0,
        deviation: int = 30,
        magic: int = 999001,
        dry_run: bool = True,
        mt5_client: Any = mt5,
    ) -> None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol must be a non-empty string")

        if not 0 < risk_percent <= 2:
            raise ValueError(
                "risk_percent must be greater than 0 and not exceed 2"
            )

        if deviation < 0:
            raise ValueError("deviation must not be negative")

        self.symbol = symbol.strip()
        self.signal_path = TARGET_FOLDER / file_name
        self.risk_percent = float(risk_percent)
        self.deviation = int(deviation)
        self.magic = int(magic)
        self.dry_run = dry_run
        self.mt5 = mt5_client
        self._initialized = False

    # =========================================================
    # MT5 connection
    # =========================================================
    def initialize(self) -> None:
        if not self.mt5.initialize():
            raise RuntimeError(
                f"MT5 initialize failed: {self.mt5.last_error()}"
            )

        self._initialized = True

    def shutdown(self) -> None:
        if self._initialized:
            self.mt5.shutdown()
            self._initialized = False

    # =========================================================
    # Load signal
    # =========================================================
    def load_signal(self) -> dict[str, Any]:
        if not self.signal_path.exists():
            raise FileNotFoundError(
                f"Signal file not found: {self.signal_path}"
            )

        if not self.signal_path.is_file():
            raise FileNotFoundError(
                f"Signal path is not a file: {self.signal_path}"
            )

        try:
            with self.signal_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                signal = json.load(file)

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in signal file: {error}"
            ) from error

        except OSError as error:
            raise RuntimeError(
                f"Failed to read signal file: {error}"
            ) from error

        if not isinstance(signal, dict):
            raise ValueError("Signal JSON must be an object")

        print_log("load signal success!!")

        return signal

    # =========================================================
    # Signal helpers
    # =========================================================
    @staticmethod
    def get_number(
        signal: dict[str, Any],
        *keys: str,
    ) -> float:
        for key in keys:
            if key not in signal:
                continue

            value = signal[key]

            if isinstance(value, bool):
                raise ValueError(f"'{key}' must be numeric")

            try:
                number = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"'{key}' must be numeric"
                ) from error

            if not math.isfinite(number):
                raise ValueError(
                    f"'{key}' must be a finite number"
                )

            return number

        expected = " or ".join(f"'{key}'" for key in keys)
        raise KeyError(f"Missing required field: {expected}")

    @staticmethod
    def get_position_type(
        signal: dict[str, Any],
    ) -> str:
        value = signal.get("type_position")

        if not isinstance(value, str):
            raise ValueError(
                "'type_position' must be a string"
            )

        position_type = value.strip().lower()

        valid_types = {
            "buy",
            "sell",
            "buy_stop",
            "sell_stop",
            "buy_limit",
            "sell_limit",
            "none",
        }

        if position_type not in valid_types:
            raise ValueError(
                f"Invalid type_position: {value}"
            )

        return position_type

    # =========================================================
    # Symbol information
    # =========================================================
    def get_symbol_info(self) -> Any:
        info = self.mt5.symbol_info(self.symbol)

        if info is None:
            raise RuntimeError(
                f"Symbol '{self.symbol}' not found: "
                f"{self.mt5.last_error()}"
            )

        if not info.visible:
            if not self.mt5.symbol_select(self.symbol, True):
                raise RuntimeError(
                    f"Failed to select symbol '{self.symbol}': "
                    f"{self.mt5.last_error()}"
                )

            info = self.mt5.symbol_info(self.symbol)

            if info is None:
                raise RuntimeError(
                    f"Failed to reload symbol info "
                    f"for '{self.symbol}'"
                )

        return info

    # =========================================================
    # Price and order type
    # =========================================================
    def resolve_order_parameters(
        self,
        signal: dict[str, Any],
        position_type: str,
        tick: Any,
    ) -> tuple[int, int, int, float, bool]:
        """
        Returns:
            action
            order_type
            calculation_order_type
            entry_price
            is_pending
        """

        if position_type == "buy":
            return (
                self.mt5.TRADE_ACTION_DEAL,
                self.mt5.ORDER_TYPE_BUY,
                self.mt5.ORDER_TYPE_BUY,
                float(tick.ask),
                False,
            )

        if position_type == "sell":
            return (
                self.mt5.TRADE_ACTION_DEAL,
                self.mt5.ORDER_TYPE_SELL,
                self.mt5.ORDER_TYPE_SELL,
                float(tick.bid),
                False,
            )

        entry_price = self.get_number(
            signal,
            "price",
            "entry",
        )

        pending_map = {
            "buy_stop": (
                self.mt5.ORDER_TYPE_BUY_STOP,
                self.mt5.ORDER_TYPE_BUY,
            ),
            "sell_stop": (
                self.mt5.ORDER_TYPE_SELL_STOP,
                self.mt5.ORDER_TYPE_SELL,
            ),
            "buy_limit": (
                self.mt5.ORDER_TYPE_BUY_LIMIT,
                self.mt5.ORDER_TYPE_BUY,
            ),
            "sell_limit": (
                self.mt5.ORDER_TYPE_SELL_LIMIT,
                self.mt5.ORDER_TYPE_SELL,
            ),
        }

        order_type, calculation_type = pending_map[position_type]

        return (
            self.mt5.TRADE_ACTION_PENDING,
            order_type,
            calculation_type,
            entry_price,
            True,
        )

    # =========================================================
    # Validate entry, SL and TP
    # =========================================================
    def validate_prices(
        self,
        position_type: str,
        price: float,
        sl: float,
        tp: float,
        tick: Any,
        info: Any,
    ) -> None:
        stop_level = float(info.trade_stops_level) * float(info.point)
        tolerance = float(info.point) / 2

        buy_types = {
            "buy",
            "buy_stop",
            "buy_limit",
        }

        sell_types = {
            "sell",
            "sell_stop",
            "sell_limit",
        }

        if position_type in buy_types:
            if not sl < price < tp:
                raise ValueError(
                    "BUY order requires SL < entry < TP"
                )

        elif position_type in sell_types:
            if not tp < price < sl:
                raise ValueError(
                    "SELL order requires TP < entry < SL"
                )

        if abs(price - sl) + tolerance < stop_level:
            raise ValueError(
                f"SL is too close to entry. "
                f"Minimum distance: {stop_level}"
            )

        if abs(tp - price) + tolerance < stop_level:
            raise ValueError(
                f"TP is too close to entry. "
                f"Minimum distance: {stop_level}"
            )

        if position_type == "buy_stop":
            distance = price - float(tick.ask)

            if distance <= 0:
                raise ValueError(
                    "BUY_STOP entry must be above ASK"
                )

            if distance + tolerance < stop_level:
                raise ValueError(
                    "BUY_STOP entry is too close to ASK"
                )

        elif position_type == "sell_stop":
            distance = float(tick.bid) - price

            if distance <= 0:
                raise ValueError(
                    "SELL_STOP entry must be below BID"
                )

            if distance + tolerance < stop_level:
                raise ValueError(
                    "SELL_STOP entry is too close to BID"
                )

        elif position_type == "buy_limit":
            distance = float(tick.ask) - price

            if distance <= 0:
                raise ValueError(
                    "BUY_LIMIT entry must be below ASK"
                )

            if distance + tolerance < stop_level:
                raise ValueError(
                    "BUY_LIMIT entry is too close to ASK"
                )

        elif position_type == "sell_limit":
            distance = price - float(tick.bid)

            if distance <= 0:
                raise ValueError(
                    "SELL_LIMIT entry must be above BID"
                )

            if distance + tolerance < stop_level:
                raise ValueError(
                    "SELL_LIMIT entry is too close to BID"
                )

    # =========================================================
    # Volume normalization
    # =========================================================
    @staticmethod
    def normalize_volume(
        raw_volume: float,
        info: Any,
    ) -> float:
        if raw_volume <= 0:
            raise ValueError("Calculated volume must be positive")

        volume_min = Decimal(str(info.volume_min))
        volume_max = Decimal(str(info.volume_max))
        volume_step = Decimal(str(info.volume_step))
        raw = Decimal(str(raw_volume))

        if volume_step <= 0:
            raise ValueError("Invalid symbol volume_step")

        raw = min(raw, volume_max)

        step_count = (
            raw / volume_step
        ).to_integral_value(rounding=ROUND_DOWN)

        normalized = step_count * volume_step

        if normalized < volume_min:
            raise ValueError(
                f"Calculated volume {raw_volume:.8f} "
                f"is below broker minimum {info.volume_min}. "
                f"Using minimum lot would exceed risk."
            )

        decimal_places = max(
            0,
            -volume_step.normalize().as_tuple().exponent,
        )

        return round(float(normalized), decimal_places)

    # =========================================================
    # Risk-based lot calculation
    # =========================================================
    def calculate_volume(
        self,
        signal: dict[str, Any],
        calculation_order_type: int,
        price: float,
        sl: float,
        info: Any,
    ) -> tuple[float, float, float]:
        account = self.mt5.account_info()

        if account is None:
            raise RuntimeError(
                f"Failed to get account info: "
                f"{self.mt5.last_error()}"
            )

        balance = float(account.balance)

        if balance <= 0:
            raise ValueError(
                f"Invalid account balance: {balance}"
            )

        risk_amount = balance * (self.risk_percent / 100)

        loss_for_one_lot = self.mt5.order_calc_profit(
            calculation_order_type,
            self.symbol,
            1.0,
            price,
            sl,
        )

        if loss_for_one_lot is None:
            raise RuntimeError(
                f"order_calc_profit failed: "
                f"{self.mt5.last_error()}"
            )

        loss_for_one_lot = abs(float(loss_for_one_lot))

        if loss_for_one_lot <= 0:
            raise ValueError(
                "Loss for one lot must be greater than zero"
            )

        maximum_risk_lot = risk_amount / loss_for_one_lot

        signal_lot = self.get_number(
            signal,
            "lot",
            "volume",
        )

        if signal_lot <= 0:
            raise ValueError(
                "Signal lot must be greater than zero"
            )

        # ใช้ lot ที่ต่ำกว่า ระหว่าง GPT signal กับ risk calculation
        raw_volume = min(
            signal_lot,
            maximum_risk_lot,
        )

        volume = self.normalize_volume(
            raw_volume,
            info,
        )

        estimated_loss = self.mt5.order_calc_profit(
            calculation_order_type,
            self.symbol,
            volume,
            price,
            sl,
        )

        if estimated_loss is None:
            raise RuntimeError(
                f"Failed to verify final risk: "
                f"{self.mt5.last_error()}"
            )

        estimated_loss = abs(float(estimated_loss))

        # ป้องกัน floating-point หรือ broker specification ผิดปกติ
        if estimated_loss > risk_amount + 0.01:
            raise ValueError(
                f"Final risk {estimated_loss:.2f} exceeds "
                f"maximum risk {risk_amount:.2f}"
            )

        return volume, risk_amount, estimated_loss

    # =========================================================
    # Filling mode
    # =========================================================
    def get_filling_mode(
        self,
        info: Any,
        is_pending: bool,
    ) -> int:
        # Pending order ใช้ RETURN
        if is_pending:
            return self.mt5.ORDER_FILLING_RETURN

        market_execution = getattr(
            self.mt5,
            "SYMBOL_TRADE_EXECUTION_MARKET",
            2,
        )

        # RETURN ใช้ได้กับ execution mode ที่ไม่ใช่ Market Execution
        if info.trade_exemode != market_execution:
            return self.mt5.ORDER_FILLING_RETURN

        filling_flags = int(info.filling_mode)

        symbol_filling_ioc = getattr(
            self.mt5,
            "SYMBOL_FILLING_IOC",
            2,
        )

        symbol_filling_fok = getattr(
            self.mt5,
            "SYMBOL_FILLING_FOK",
            1,
        )

        if filling_flags & symbol_filling_ioc:
            return self.mt5.ORDER_FILLING_IOC

        if filling_flags & symbol_filling_fok:
            return self.mt5.ORDER_FILLING_FOK

        raise RuntimeError(
            f"No supported filling mode for '{self.symbol}'. "
            f"filling_mode={filling_flags}"
        )

    # =========================================================
    # Build request
    # =========================================================
    def build_request(
        self,
        signal: dict[str, Any],
    ) -> dict[str, Any] | None:
        position_type = self.get_position_type(signal)

        if position_type == "none":
            return None

        info = self.get_symbol_info()

        tick = self.mt5.symbol_info_tick(self.symbol)

        if tick is None:
            raise RuntimeError(
                f"No tick data for '{self.symbol}': "
                f"{self.mt5.last_error()}"
            )

        if float(tick.ask) <= 0 or float(tick.bid) <= 0:
            raise RuntimeError(
                f"Invalid tick prices for '{self.symbol}'"
            )

        (
            action,
            order_type,
            calculation_order_type,
            price,
            is_pending,
        ) = self.resolve_order_parameters(
            signal=signal,
            position_type=position_type,
            tick=tick,
        )

        digits = int(info.digits)

        price = round(float(price), digits)
        sl = round(self.get_number(signal, "SL", "sl"), digits)
        tp = round(self.get_number(signal, "TP", "tp"), digits)

        self.validate_prices(
            position_type=position_type,
            price=price,
            sl=sl,
            tp=tp,
            tick=tick,
            info=info,
        )

        volume, risk_amount, estimated_loss = (
            self.calculate_volume(
                signal=signal,
                calculation_order_type=calculation_order_type,
                price=price,
                sl=sl,
                info=info,
            )
        )

        filling_mode = self.get_filling_mode(
            info=info,
            is_pending=is_pending,
        )

        request: dict[str, Any] = {
            "action": action,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "gpt",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        market_execution = getattr(
            self.mt5,
            "SYMBOL_TRADE_EXECUTION_MARKET",
            2,
        )

        # Pending ต้องมี price
        # Market order ที่ไม่ใช่ Market Execution ต้องมี price
        if (
            is_pending
            or info.trade_exemode != market_execution
        ):
            request["price"] = price

        print_log(f"type_position: {position_type}")
        print_log(f"signal lot: {self.get_number(signal, 'lot', 'volume')}")
        print_log(f"final lot: {volume}")
        print_log(f"maximum risk amount: {risk_amount:.2f}")
        print_log(f"estimated SL loss: {estimated_loss:.2f}")

        print_log("build request success")

        return request

    # =========================================================
    # Check request
    # =========================================================
    def check_request(
        self,
        request: dict[str, Any],
    ) -> Any:
        result = self.mt5.order_check(request)

        if result is None:
            raise RuntimeError(
                f"order_check returned None: "
                f"{self.mt5.last_error()}"
            )

        if result.retcode != 0:
            raise RuntimeError(
                f"Order check failed: "
                f"retcode={result.retcode}, "
                f"comment={result.comment}"
            )

        print_log(
            f"Order check passed: "
            f"retcode={result.retcode}, "
            f"comment={result.comment}"
        )

        return result

    # =========================================================
    # Send order
    # =========================================================
    def send_order(
        self,
        request: dict[str, Any],
    ) -> Any:
        result = self.mt5.order_send(request)

        if result is None:
            raise RuntimeError(
                f"order_send returned None: "
                f"{self.mt5.last_error()}"
            )

        success_codes = {
            self.mt5.TRADE_RETCODE_DONE,
            self.mt5.TRADE_RETCODE_PLACED,
        }

        done_partial = getattr(
            self.mt5,
            "TRADE_RETCODE_DONE_PARTIAL",
            None,
        )

        if done_partial is not None:
            success_codes.add(done_partial)

        if result.retcode not in success_codes:
            raise RuntimeError(
                f"Order failed: "
                f"retcode={result.retcode}, "
                f"comment={result.comment}"
            )

        print_log("Order success")
        print_log(f"Retcode: {result.retcode}")
        print_log(f"Order ticket: {result.order}")
        print_log(f"Deal ticket: {result.deal}")
        print_log(f"Volume: {result.volume}")
        print_log(f"Price: {result.price}")

        return result

    # =========================================================
    # Main
    # =========================================================
    def run(self) -> Any | None:
        self.initialize()

        try:
            signal = self.load_signal()
            request = self.build_request(signal)

            if request is None:
                print_log("Signal is NONE. No order sent.")
                return None

            print_log("Request:", request)

            self.check_request(request)

            if self.dry_run:
                print_log(
                    "DRY RUN enabled. "
                    "Order was checked but not sent."
                )
                return None

            return self.send_order(request)

        finally:
            self.shutdown()


if __name__ == "__main__":
    trader = MT5AutoTrader(
        symbol="BTCUSDc",
        file_name="result_gpt.json",
        risk_percent=2.0,

        # True = ตรวจสอบอย่างเดียว ไม่เปิด order
        # False = ส่ง order จริง
        dry_run=True,
    )

    trader.run()