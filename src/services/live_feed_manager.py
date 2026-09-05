from __future__ import annotations

import threading
from datetime import datetime, timezone

from src.data.candle_engine import CandleEngine
from src.data.historical_candle_loader import (
    load_historical_candles,
    refresh_intraday_candles,
)
from src.data.live_candle_store import LiveCandleStore
from src.services.live_analysis_service import LiveAnalysisService


class LiveFeedManager:
    """
    Own candles and analysis for one exact Upstox instrument.

    Startup deliberately loads ONLY the selected timeframe.

    Other timeframes are loaded lazily when the user selects them.
    This prevents startup from making 14 broker HTTP requests
    (historical + intraday for seven intervals).
    """

    SUPPORTED_INTERVALS = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "10m": 600,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
    }

    def __init__(
        self,
        symbol: str,
        instrument_key: str,
        max_candles: int = 200,
        on_bootstrap_complete=None,
    ):
        if not symbol or not symbol.strip():
            raise ValueError("Symbol is required.")

        if not instrument_key or not instrument_key.strip():
            raise ValueError("instrument_key is required.")

        if max_candles <= 0:
            raise ValueError("max_candles must be greater than 0.")

        self.symbol = symbol.strip().upper()
        self.instrument_key = instrument_key.strip()
        self.max_candles = max_candles
        self.on_bootstrap_complete = on_bootstrap_complete
        self._bootstrap_generation = 0

        self._lock = threading.RLock()

        self.selected_interval: str | None = None

        self.candle_engines: dict[str, CandleEngine] = {}
        self.candle_stores: dict[str, LiveCandleStore] = {}

        self.analysis_service = LiveAnalysisService()

        self.latest_analysis = None
        self.latest_tick = None
        self.latest_completed_candles: dict[str, dict] = {}

        self.running = False
        self.started_at = None
        self.last_analysis_at = None
        self.analysis_error = None

    # ================================================================
    # INTERVAL
    # ================================================================

    def validate_interval(self, interval: str) -> str:
        interval = (interval or "").strip().lower()

        if interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported intervals: "
                f"{list(self.SUPPORTED_INTERVALS)}"
            )

        return interval

    # ================================================================
    # LOAD ONE INTERVAL
    # ================================================================

    def _load_interval(self, interval: str) -> None:
        """
        Load one timeframe without holding the manager lock while waiting
        for broker HTTP requests.

        Historical data is the critical path. It gives us enough candles
        for immediate indicators/strategies/AI without waiting for the
        optional current-day intraday endpoint.
        """
        interval = self.validate_interval(interval)

        with self._lock:
            if interval in self.candle_engines:
                return

            generation = self._bootstrap_generation

            if not self.running:
                return

        print()
        print("-" * 70)
        print(f"LOADING TIMEFRAME: {interval}")
        print("-" * 70)

        live_store = load_historical_candles(
            symbol=self.symbol,
            instrument_key=self.instrument_key,
            interval=interval,
            period="5d",
            max_candles=self.max_candles,
        )

        engine = CandleEngine(
            self.symbol,
            interval,
            self.instrument_key,
        )

        with self._lock:
            if (
                not self.running
                or generation != self._bootstrap_generation
            ):
                return

            latest_tick = (
                dict(self.latest_tick)
                if self.latest_tick
                else None
            )

            self.candle_engines[interval] = engine

            # IMPORTANT OPTIMIZATION:
            # The loader already returns a prepared LiveCandleStore.
            # Do not copy historical candles one-by-one with add_candle().
            self.candle_stores[interval] = live_store

        print(
            f"Loaded {live_store.count()} completed "
            f"{interval} candles."
        )

        # Replay the newest live tick so the current forming candle
        # becomes available immediately.
        if latest_tick:
            completed = engine.update(
                price=latest_tick["price"],
                timestamp_ms=latest_tick["timestamp_ms"],
                quantity=latest_tick["quantity"],
            )

            if completed:
                with self._lock:
                    if (
                        self.running
                        and generation == self._bootstrap_generation
                    ):
                        live_store.add_candle(completed)
                        self.latest_completed_candles[
                            interval
                        ] = completed

        print(f"Timeframe {interval} ready from historical data.")

        # Intraday data is supplemental and must not delay chart readiness
        # or initial analysis.
        def refresh_intraday():
            try:
                added = refresh_intraday_candles(
                    symbol=self.symbol,
                    interval=interval,
                    instrument_key=self.instrument_key,
                    store=live_store,
                    max_candles=self.max_candles,
                )

                with self._lock:
                    valid = (
                        self.running
                        and generation == self._bootstrap_generation
                        and self.candle_stores.get(interval) is live_store
                    )

                    current_price = (
                        self.latest_tick["price"]
                        if self.latest_tick
                        else None
                    )

                    should_analyze = (
                        valid
                        and self.selected_interval == interval
                    )

                    if should_analyze and added > 0:
                        self._run_analysis(
                            current_price=current_price
                        )

                    callback = (
                        self.on_bootstrap_complete
                        if valid
                        else None
                    )

                if callback and added > 0:
                    try:
                        callback()
                    except Exception as exc:
                        print(
                            "INTRADAY UPDATE CALLBACK ERROR: "
                            f"{type(exc).__name__}: {exc}"
                        )

            except Exception as exc:
                print(
                    "BACKGROUND INTRADAY REFRESH ERROR: "
                    f"{type(exc).__name__}: {exc}"
                )

        threading.Thread(
            target=refresh_intraday,
            name=f"IntradayRefresh-{interval}",
            daemon=True,
        ).start()

        print("-" * 70)
        print()

    # ================================================================
    # START
    # ================================================================

    def start(self, interval: str = "1m"):
        interval = self.validate_interval(interval)

        with self._lock:
            self._bootstrap_generation += 1

            self.candle_engines.clear()
            self.candle_stores.clear()
            self.latest_completed_candles = {}

            self.selected_interval = interval
            self.latest_analysis = None
            self.latest_tick = None

            self.running = True
            self.started_at = datetime.now(timezone.utc).isoformat()
            self.last_analysis_at = None
            self.analysis_error = "Loading historical candles..."

            generation = self._bootstrap_generation

        print()
        print("=" * 70)
        print("LIVE FEED MANAGER START")
        print("=" * 70)
        print(f"Symbol          : {self.symbol}")
        print(f"Instrument      : {self.instrument_key}")
        print(f"Selected        : {interval}")
        print("Startup policy   : background historical bootstrap")
        print("Store bootstrap  : bulk LiveCandleStore load")
        print("=" * 70)

        def bootstrap():
            try:
                self._load_interval(interval)

                with self._lock:
                    if (
                        not self.running
                        or generation != self._bootstrap_generation
                    ):
                        return

                    self._run_analysis(
                        current_price=(
                            self.latest_tick["price"]
                            if self.latest_tick
                            else None
                        )
                    )

                    callback = self.on_bootstrap_complete

                if callback:
                    try:
                        callback()
                    except Exception as exc:
                        print(
                            "BOOTSTRAP CALLBACK ERROR: "
                            f"{type(exc).__name__}: {exc}"
                        )

            except Exception as exc:
                with self._lock:
                    if (
                        self.running
                        and generation == self._bootstrap_generation
                    ):
                        self.analysis_error = (
                            f"Bootstrap "
                            f"{type(exc).__name__}: {exc}"
                        )

                print(
                    "HISTORICAL BOOTSTRAP ERROR: "
                    f"{type(exc).__name__}: {exc}"
                )

        threading.Thread(
            target=bootstrap,
            name=f"CandleBootstrap-{interval}",
            daemon=True,
        ).start()

    # ================================================================
    # CHANGE INTERVAL
    # ================================================================

    def set_interval(self, interval: str):
        interval = self.validate_interval(interval)

        with self._lock:
            if not self.running:
                raise RuntimeError("Live feed is not running.")

            old_interval = self.selected_interval
            self.selected_interval = interval
            self.latest_analysis = None
            self.analysis_error = None

            already_loaded = interval in self.candle_engines

            latest_price = (
                self.latest_tick["price"]
                if self.latest_tick
                else None
            )

            generation = self._bootstrap_generation

        if not already_loaded:
            self._load_interval(interval)

        with self._lock:
            if (
                not self.running
                or generation != self._bootstrap_generation
            ):
                return {
                    "changed": old_interval != interval,
                    "old_interval": old_interval,
                    "interval": interval,
                }

            self._run_analysis(current_price=latest_price)

            return {
                "changed": old_interval != interval,
                "old_interval": old_interval,
                "interval": interval,
            }

    # ================================================================
    # LIVE TICK
    # ================================================================

    def process_tick(
        self,
        price: float,
        timestamp_ms: int,
        quantity: int = 0,
    ):
        with self._lock:
            if not self.running:
                return {}

            price = float(price)
            timestamp_ms = int(timestamp_ms)
            quantity = int(quantity)

            self.latest_tick = {
                "symbol": self.symbol,
                "instrument_key": self.instrument_key,
                "price": price,
                "timestamp_ms": timestamp_ms,
                "quantity": quantity,
            }

            completed: dict[str, dict] = {}

            for interval, engine in self.candle_engines.items():
                candle = engine.update(
                    price,
                    timestamp_ms,
                    quantity,
                )

                if candle:
                    completed[interval] = candle

            for interval, candle in completed.items():
                store = self.candle_stores[interval]
                store.add_candle(candle)

                self.latest_completed_candles[
                    interval
                ] = candle

            if self.selected_interval in completed:
                self._run_analysis(current_price=price)

            return completed

    # ================================================================
    # ANALYSIS
    # ================================================================

    def _run_analysis(self, current_price: float | None = None):
        interval = self.selected_interval

        if not interval:
            return None

        store = self.candle_stores.get(interval)

        if not store:
            return None

        candles = store.get_candles()

        if len(candles) < 60:
            self.analysis_error = (
                f"Waiting for enough completed "
                f"{interval} candles "
                f"({len(candles)}/60)."
            )
            return None

        try:
            result = self.analysis_service.analyze(
                candles,
                current_price=current_price,
            )

            self.latest_analysis = result
            self.last_analysis_at = datetime.now(
                timezone.utc
            ).isoformat()
            self.analysis_error = None

            return result

        except Exception as exc:
            self.analysis_error = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                f"LIVE ANALYSIS ERROR: "
                f"{self.analysis_error}"
            )

            return None

    # ================================================================
    # CANDLES
    # ================================================================

    def get_candles(self, interval: str | None = None):
        with self._lock:
            i = self.validate_interval(
                interval or self.selected_interval
            )

            store = self.candle_stores.get(i)

            if not store:
                return []

            return store.get_candles()

    # ================================================================
    # DATAFRAME
    # ================================================================

    def get_dataframe(self, interval: str | None = None):
        with self._lock:
            i = self.validate_interval(
                interval or self.selected_interval
            )

            store = self.candle_stores.get(i)

            if not store:
                return None

            return store.get_dataframe()

    # ================================================================
    # CURRENT CANDLE
    # ================================================================

    def get_current_candle(self, interval: str | None = None):
        with self._lock:
            i = self.validate_interval(
                interval or self.selected_interval
            )

            engine = self.candle_engines.get(i)

            if not engine:
                return None

            return engine.get_current_candle()

    # ================================================================
    # LATEST TICK
    # ================================================================

    def get_latest_tick(self):
        with self._lock:
            return (
                dict(self.latest_tick)
                if self.latest_tick
                else None
            )

    # ================================================================
    # LATEST ANALYSIS
    # ================================================================

    def get_latest_analysis(self):
        with self._lock:
            return self.latest_analysis

    # ================================================================
    # STATE
    # ================================================================

    def get_state(self):
        with self._lock:
            return {
                "running": self.running,
                "symbol": self.symbol,
                "instrument_key": self.instrument_key,
                "selected_interval": self.selected_interval,
                "candle_counts": {
                    interval: store.count()
                    for interval, store in self.candle_stores.items()
                },
                "loaded_intervals": list(
                    self.candle_stores.keys()
                ),
                "latest_tick": self.latest_tick,
                "analysis_available": (
                    self.latest_analysis is not None
                ),
                "analysis_error": self.analysis_error,
                "last_analysis_at": self.last_analysis_at,
                "started_at": self.started_at,
            }

    # ================================================================
    # STOP
    # ================================================================

    def stop(self):
        with self._lock:
            self._bootstrap_generation += 1
            self.running = False

            self.candle_engines.clear()
            self.candle_stores.clear()

            self.selected_interval = None

            self.latest_analysis = None
            self.latest_tick = None
            self.latest_completed_candles = {}

            self.started_at = None
            self.last_analysis_at = None
            self.analysis_error = None
