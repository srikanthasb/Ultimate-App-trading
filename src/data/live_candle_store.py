from __future__ import annotations

import pandas as pd


class LiveCandleStore:
    """Rolling in-memory OHLC candle store.

    Same timestamp -> update existing candle.
    Newer timestamp -> append.
    Older timestamp -> ignore.
    """

    def __init__(self, max_candles: int = 200):
        if max_candles <= 0:
            raise ValueError("max_candles must be greater than 0.")
        self.max_candles = max_candles
        self.candles: list[dict] = []

    @staticmethod
    def _normalize_timestamp(timestamp) -> pd.Timestamp:
        if timestamp is None:
            raise ValueError("Candle timestamp is required.")
        ts = pd.to_datetime(timestamp, utc=True)
        if pd.isna(ts):
            raise ValueError(f"Invalid candle timestamp: {timestamp}")
        return ts

    @staticmethod
    def _validate(candle: dict) -> None:
        if not candle:
            raise ValueError("Candle is empty.")
        required = [
            "symbol", "interval", "timestamp",
            "open", "high", "low", "close", "volume"
        ]
        for field in required:
            if field not in candle:
                raise ValueError(f"Candle is missing required field: {field}")

    def _sort_and_trim(self) -> None:
        self.candles.sort(
            key=lambda c: self._normalize_timestamp(c["timestamp"])
        )
        if len(self.candles) > self.max_candles:
            self.candles = self.candles[-self.max_candles:]

    def add_candle(self, candle: dict) -> None:
        """Add a candle, replacing an existing candle with the same timestamp."""
        self._validate(candle)

        new_candle = candle.copy()
        new_ts = self._normalize_timestamp(new_candle["timestamp"])
        new_candle["timestamp"] = new_ts.isoformat()

        for i, existing in enumerate(self.candles):
            if self._normalize_timestamp(existing["timestamp"]) == new_ts:
                self.candles[i] = new_candle
                self._sort_and_trim()
                return

        if self.candles:
            latest = max(
                self._normalize_timestamp(c["timestamp"])
                for c in self.candles
            )
            if new_ts < latest:
                return

        self.candles.append(new_candle)
        self._sort_and_trim()

    def get_candles(self) -> list:
        return [c.copy() for c in self.candles]

    def get_dataframe(self) -> pd.DataFrame:
        if not self.candles:
            return pd.DataFrame()

        data = pd.DataFrame(self.get_candles())
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        data = data.sort_values("timestamp").set_index("timestamp")

        return data.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })

    def get_latest(self):
        return self.candles[-1].copy() if self.candles else None

    def count(self) -> int:
        return len(self.candles)

    def clear(self) -> None:
        self.candles.clear()
