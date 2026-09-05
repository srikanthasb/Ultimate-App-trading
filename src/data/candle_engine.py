from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


class CandleEngine:
    """
    Converts live market ticks into OHLCV candles.

    Supported intervals:
        1m
        3m
        5m
        10m
        15m
        30m
        1h

    Candle boundaries are anchored to the NSE market session
    starting at 09:15 IST.

    The engine is deterministic.
    No AI or LLM is involved.
    """

    INTERVALS = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "10m": 600,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
    }

    MARKET_START_HOUR = 9
    MARKET_START_MINUTE = 15

    def __init__(self, symbol: str, interval: str = "1m", instrument_key: str | None = None):
        if interval not in self.INTERVALS:
            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported intervals: {list(self.INTERVALS.keys())}"
            )

        self.symbol = symbol
        self.instrument_key = instrument_key
        self.interval = interval
        self.interval_seconds = self.INTERVALS[interval]

        self.current_candle = None

    def _get_bucket_start(self, timestamp_ms: int) -> datetime:
        """
        Convert tick timestamp into the beginning of its candle interval.

        Candle boundaries are anchored to the NSE session start:
            09:15 IST

        Examples:

            5m:
                09:15
                09:20
                09:25
                ...

            30m:
                09:15
                09:45
                10:15
                ...

            1h:
                09:15
                10:15
                11:15
                ...
        """

        timestamp_seconds = timestamp_ms / 1000

        dt = datetime.fromtimestamp(
            timestamp_seconds,
            tz=timezone.utc,
        ).astimezone(IST)

        # NSE market session anchor for the same trading day.
        session_start = dt.replace(
            hour=self.MARKET_START_HOUR,
            minute=self.MARKET_START_MINUTE,
            second=0,
            microsecond=0,
        )

        # For normal NSE live ticks, this should always be >= 09:15.
        # Keep a defensive fallback for timestamps before market open.
        if dt < session_start:
            return session_start

        elapsed_seconds = int(
            (dt - session_start).total_seconds()
        )

        bucket_offset = (
            elapsed_seconds // self.interval_seconds
        ) * self.interval_seconds

        bucket = (
            session_start
            + timedelta(seconds=bucket_offset)
        )

        return bucket

    def update(
        self,
        price: float,
        timestamp_ms: int,
        quantity: int = 0,
    ):
        """
        Process one live market tick.

        Returns:
            completed candle when a new interval starts
            None while the current candle is still forming
        """

        if price is None:
            return None

        bucket_start = self._get_bucket_start(timestamp_ms)

        # First tick
        if self.current_candle is None:
            self.current_candle = {
                "symbol": self.symbol,
                "instrument_key": self.instrument_key,
                "interval": self.interval,
                "timestamp": bucket_start.isoformat(),
                "open": float(price),
                "high": float(price),
                "low": float(price),
                "close": float(price),
                "volume": int(quantity),
            }

            return None

        # Same candle
        current_timestamp = self.current_candle["timestamp"]

        if current_timestamp == bucket_start.isoformat():
            self.current_candle["high"] = max(
                self.current_candle["high"],
                float(price),
            )

            self.current_candle["low"] = min(
                self.current_candle["low"],
                float(price),
            )

            self.current_candle["close"] = float(price)

            self.current_candle["volume"] += int(quantity)

            return None

        # New candle started.
        completed_candle = self.current_candle

        self.current_candle = {
            "symbol": self.symbol,
            "instrument_key": self.instrument_key,
            "interval": self.interval,
            "timestamp": bucket_start.isoformat(),
            "open": float(price),
            "high": float(price),
            "low": float(price),
            "close": float(price),
            "volume": int(quantity),
        }

        return completed_candle

    def get_current_candle(self):
        """
        Return the currently forming candle.
        """

        return self.current_candle