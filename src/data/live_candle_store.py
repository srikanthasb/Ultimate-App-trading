from __future__ import annotations

from bisect import bisect_left
from typing import Iterable

import pandas as pd


class LiveCandleStore:
    """Fast rolling in-memory OHLC candle store.

    Behavior:
    - Bootstrap candles can be loaded in one operation.
    - Same timestamp -> update existing candle.
    - Newer timestamp -> append.
    - Older timestamp -> ignore.
    - Candles remain chronologically ordered.
    - Expensive timestamp parsing is avoided during normal live updates.
    """

    def __init__(self, max_candles: int = 200):
        if max_candles <= 0:
            raise ValueError("max_candles must be greater than 0.")

        self.max_candles = max_candles

        # Public candle representation remains a list of dictionaries.
        self.candles: list[dict] = []

        # Internal normalized timestamps.
        # Keeping these separately avoids repeatedly calling
        # pd.to_datetime() during live updates.
        self._timestamps: list[pd.Timestamp] = []

    # ============================================================
    # TIMESTAMP
    # ============================================================

    @staticmethod
    def _normalize_timestamp(timestamp) -> pd.Timestamp:
        if timestamp is None:
            raise ValueError("Candle timestamp is required.")

        ts = pd.to_datetime(timestamp, utc=True)

        if pd.isna(ts):
            raise ValueError(
                f"Invalid candle timestamp: {timestamp}"
            )

        return ts

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate(candle: dict) -> None:
        if not candle:
            raise ValueError("Candle is empty.")

        required = [
            "symbol",
            "interval",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for field in required:
            if field not in candle:
                raise ValueError(
                    f"Candle is missing required field: {field}"
                )

    # ============================================================
    # NORMALIZE CANDLE
    # ============================================================

    def _prepare_candle(
        self,
        candle: dict,
    ) -> tuple[dict, pd.Timestamp]:
        """Validate and normalize a candle once."""

        self._validate(candle)

        new_candle = candle.copy()

        timestamp = self._normalize_timestamp(
            new_candle["timestamp"]
        )

        # Keep external representation compatible with the
        # existing application.
        new_candle["timestamp"] = timestamp.isoformat()

        return new_candle, timestamp

    # ============================================================
    # TRIM
    # ============================================================

    def _trim(self) -> None:
        """Keep only the newest max_candles candles."""

        excess = len(self.candles) - self.max_candles

        if excess <= 0:
            return

        del self.candles[:excess]
        del self._timestamps[:excess]

    # ============================================================
    # BULK LOAD
    # ============================================================

    def load_candles(
        self,
        candles: Iterable[dict],
    ) -> None:
        """Fast bootstrap method.

        The historical loader already returns candles in chronological
        order and already limits them to the required number.

        Therefore we normalize and store them in one operation rather
        than calling add_candle() repeatedly.

        Duplicate timestamps are handled safely by keeping the latest
        candle for each timestamp.
        """

        prepared: dict[pd.Timestamp, dict] = {}

        for candle in candles:
            new_candle, timestamp = self._prepare_candle(candle)

            # Same timestamp:
            # later candle wins.
            prepared[timestamp] = new_candle

        if not prepared:
            self.candles.clear()
            self._timestamps.clear()
            return

        ordered = sorted(
            prepared.items(),
            key=lambda item: item[0],
        )

        # Keep newest candles only.
        if len(ordered) > self.max_candles:
            ordered = ordered[-self.max_candles:]

        self._timestamps = [
            timestamp
            for timestamp, _ in ordered
        ]

        self.candles = [
            candle
            for _, candle in ordered
        ]

    # ============================================================
    # ADD / UPDATE
    # ============================================================

    def add_candle(self, candle: dict) -> None:
        """Add or update a single live candle.

        Fast path:
        - Same timestamp -> replace.
        - Newer timestamp -> append.
        - Older timestamp -> ignore.

        Normal live operation therefore does not require a full
        list sort or repeated timestamp conversion.
        """

        new_candle, new_ts = self._prepare_candle(candle)

        # Empty store.
        if not self._timestamps:
            self.candles.append(new_candle)
            self._timestamps.append(new_ts)
            return

        latest_ts = self._timestamps[-1]

        # --------------------------------------------------------
        # Normal live case: newer candle
        # --------------------------------------------------------

        if new_ts > latest_ts:
            self.candles.append(new_candle)
            self._timestamps.append(new_ts)

            # Trim without sorting.
            self._trim()
            return

        # --------------------------------------------------------
        # Normal live case: current candle update
        # --------------------------------------------------------

        if new_ts == latest_ts:
            self.candles[-1] = new_candle
            return

        # --------------------------------------------------------
        # Older timestamp
        # --------------------------------------------------------

        # Usually this is historical/out-of-order data and should
        # be ignored.
        #
        # However, if an older timestamp happens to already exist
        # in the store, update that candle rather than creating a
        # duplicate.
        position = bisect_left(
            self._timestamps,
            new_ts,
        )

        if (
            position < len(self._timestamps)
            and self._timestamps[position] == new_ts
        ):
            self.candles[position] = new_candle

        # Otherwise ignore the old candle.

    # ============================================================
    # GET CANDLES
    # ============================================================

    def get_candles(self) -> list[dict]:
        """Return copies of all stored candles."""

        return [
            candle.copy()
            for candle in self.candles
        ]

    # ============================================================
    # DATAFRAME
    # ============================================================

    def get_dataframe(self) -> pd.DataFrame:
        """Return candles as a pandas OHLC dataframe."""

        if not self.candles:
            return pd.DataFrame()

        # Build directly from the already-normalized candles.
        data = pd.DataFrame(self.candles)

        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            utc=True,
        )

        # Candles should already be ordered, but keeping this
        # defensive sort here makes the dataframe contract safe.
        data = (
            data
            .sort_values("timestamp")
            .set_index("timestamp")
        )

        return data.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )

    # ============================================================
    # LATEST
    # ============================================================

    def get_latest(self):
        """Return the newest candle."""

        if not self.candles:
            return None

        return self.candles[-1].copy()

    # ============================================================
    # COUNT
    # ============================================================

    def count(self) -> int:
        """Return number of stored candles."""

        return len(self.candles)

    # ============================================================
    # CLEAR
    # ============================================================

    def clear(self) -> None:
        """Remove all candles."""

        self.candles.clear()
        self._timestamps.clear()