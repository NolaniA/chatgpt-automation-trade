import MetaTrader5 as mt5
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
from datetime import datetime


@dataclass
class MT5Config:
    symbol: str = None
    timeframes: List[int] = field(default_factory=lambda: [
        mt5.TIMEFRAME_M1,
        mt5.TIMEFRAME_M5,
        mt5.TIMEFRAME_M15,
        mt5.TIMEFRAME_H1,
        mt5.TIMEFRAME_H4,
        mt5.TIMEFRAME_D1,
    ])
    bars: int = 100
    save_folder: Path = Path("/chatgpt-analyse/data_files")


class MT5DataFeed:
    def __init__(self, config: MT5Config):
        self.cfg = config
        self.save_path = Path(self.cfg.save_folder)
        self.save_path.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # Connect
    # ----------------------------
    def connect(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        info = mt5.symbol_info(self.cfg.symbol)

        if info is None:
            raise ValueError(f"Symbol '{self.cfg.symbol}' not found")

        if not info.visible:
            mt5.symbol_select(self.cfg.symbol, True)

    # ----------------------------
    # Fetch TF
    # ----------------------------
    def _fetch_tf(self, timeframe: int) -> pd.DataFrame:
        rates = mt5.copy_rates_from_pos(
            self.cfg.symbol,
            timeframe,
            0,
            self.cfg.bars
        )

        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No data for timeframe {timeframe}")

        df = pd.DataFrame(rates)
        df.columns = [
            "time", "open", "high", "low", "close",
            "tick_volume", "spread", "real_volume"
        ]
        df["time"] = pd.to_datetime(df["time"], unit="s")

        return df

    # ----------------------------
    # Multi TF
    # ----------------------------
    def get_multiple_tf(self) -> Dict[str, pd.DataFrame]:
        tf_map = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1",
        }

        result = {}

        for tf in self.cfg.timeframes:
            name = tf_map.get(tf, str(tf))
            df = self._fetch_tf(tf)
            result[name] = df

        return result

    # ----------------------------
    # Save Files
    # ----------------------------
    def save_to_csv(self, data: Dict[str, pd.DataFrame]):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for tf_name, df in data.items():
            # filename = f"{self.cfg.symbol}_{tf_name}_{timestamp}.csv"
            # filename = f"{self.cfg.symbol}_{tf_name}.csv"
            filename = f"TF_{tf_name}.csv"
            file_path = self.save_path / filename
            df.to_csv(file_path, index=False)
            # print(f"Saved: {file_path}")
        # print(f"Saved: {self.save_path}")

    # ----------------------------
    def shutdown(self):
        mt5.shutdown()


    def run_all(self):
        try:
            self.connect()

            data = self.get_multiple_tf()

            self.save_to_csv(data)

        except Exception as e:
            print(f"fetch mt5 error: {e}")

        finally:
            self.shutdown()

if __name__ == "__main__":
    config = MT5Config(
        symbol="XAUUSDm",
        timeframes=[
            mt5.TIMEFRAME_M1,
            mt5.TIMEFRAME_M15,
            mt5.TIMEFRAME_H1
        ],
        bars=100,
    )

    feed = MT5DataFeed(config)
    feed.run_all()