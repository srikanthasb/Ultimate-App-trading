import os
import threading
from datetime import datetime, timezone
from threading import RLock

import upstox_client
from dotenv import load_dotenv

from src.data.upstox_instrument_resolver import (
    UpstoxInstrumentResolver,
)
from src.services.live_feed_manager import (
    LiveFeedManager,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not UPSTOX_ACCESS_TOKEN:
    raise RuntimeError(
        "UPSTOX_ACCESS_TOKEN is missing from .env"
    )


class LiveMarketService:

    SUPPORTED_INTERVALS = [
        "1m",
        "3m",
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    ]

    def __init__(self, max_candles: int = 200):

        self.max_candles = max_candles

        # ----------------------------------------------------
        # Instrument resolver
        # ----------------------------------------------------

        self.resolver = UpstoxInstrumentResolver()

        # ----------------------------------------------------
        # Thread safety
        # ----------------------------------------------------

        self._lock = RLock()

        # ----------------------------------------------------
        # Core market objects
        # ----------------------------------------------------

        self.manager = None
        self.instrument = None

        # ----------------------------------------------------
        # WebSocket
        # ----------------------------------------------------

        self.streamer = None
        self.websocket_thread = None

        self.websocket_connected = False

        self.websocket_error = None

        self.websocket_connected_at = None

        self.last_websocket_message_at = None

        # ----------------------------------------------------
        # Duplicate LTPC protection
        # ----------------------------------------------------

        self.last_ltp_event = None

        # ----------------------------------------------------
        # Service state
        # ----------------------------------------------------

        self.running = False
        self._subscribers = set()

    # ========================================================
    # INSTRUMENT SEARCH
    # ========================================================

    def search_instruments(
        self,
        query: str,
    ) -> list[dict]:

        return self.resolver.search(
            query=query,
            exchanges="NSE",
            segments="EQ,INDEX",
            records=30,
        )

    # ========================================================
    # START
    # ========================================================

    def start(
        self,
        instrument: dict,
        interval: str = "1m",
    ):

        # ----------------------------------------------------
        # Validate interval
        # ----------------------------------------------------

        if interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported intervals: "
                f"{self.SUPPORTED_INTERVALS}"
            )

        # ----------------------------------------------------
        # Validate instrument
        # ----------------------------------------------------

        if not instrument:
            raise ValueError(
                "Instrument information is required."
            )

        instrument_key = instrument.get(
            "instrument_key"
        )

        trading_symbol = instrument.get(
            "trading_symbol"
        )

        if not instrument_key:
            raise ValueError(
                "Instrument is missing instrument_key."
            )

        if not trading_symbol:
            raise ValueError(
                "Instrument is missing trading_symbol."
            )

        with self._lock:

            # ------------------------------------------------
            # Stop any previous session
            # ------------------------------------------------

            self.stop()

            # ------------------------------------------------
            # Store selected instrument
            # ------------------------------------------------

            self.instrument = instrument

            # ------------------------------------------------
            # Reset WebSocket state
            # ------------------------------------------------

            self.streamer = None
            self.websocket_thread = None

            self.websocket_connected = False
            self.websocket_error = None
            self.websocket_connected_at = None
            self.last_websocket_message_at = None
            self.last_ltp_event = None

            # ------------------------------------------------
            # Create LiveFeedManager
            # ------------------------------------------------

            self.manager = LiveFeedManager(
                symbol=trading_symbol,
                instrument_key=instrument_key,
                max_candles=self.max_candles,
                on_bootstrap_complete=self._on_manager_bootstrap_complete,
            )

            # ------------------------------------------------
            # Bootstrap historical candles
            # ------------------------------------------------

            print()
            print("=" * 70)
            print("             STARTING LIVE MARKET SERVICE")
            print("=" * 70)
            print()

            print(
                f"Trading symbol : {trading_symbol}"
            )

            print(
                f"Instrument key : {instrument_key}"
            )

            print(
                f"Initial interval : {interval}"
            )

            print()

            print(
                "Starting LiveFeedManager bootstrap in background..."
            )

            # The manager now starts its historical bootstrap in a background
            # thread. This lets the WebSocket receive the current LTP while
            # historical candles and initial analysis are being prepared.
            self.manager.start(
                interval=interval
            )

            # Mark the service live before opening the WebSocket so callbacks
            # immediately report the correct service state.
            self.running = True

            print(
                "LiveFeedManager bootstrap started."
            )

            # ------------------------------------------------
            # Start Upstox WebSocket immediately
            # ------------------------------------------------

            self._start_websocket(
                instrument_key=instrument_key
            )

            print()
            print(
                "LiveMarketService started successfully."
            )
            print("=" * 70)
            print()

    # ========================================================
    # MANAGER BOOTSTRAP COMPLETE
    # ========================================================

    def _on_manager_bootstrap_complete(self):
        """
        Publish a fresh snapshot after historical candles and initial
        analysis are ready. The browser may already have received live ticks
        from the WebSocket before this callback fires.
        """
        print("Historical bootstrap + initial analysis complete.")
        self.publish_snapshot()

    # ========================================================
    # START WEBSOCKET
    # ========================================================

    def _start_websocket(
        self,
        instrument_key: str,
    ):

        # ----------------------------------------------------
        # Configure Upstox
        # ----------------------------------------------------

        configuration = (
            upstox_client.Configuration()
        )

        configuration.access_token = (
            UPSTOX_ACCESS_TOKEN
        )

        api_client = upstox_client.ApiClient(
            configuration
        )

        # ----------------------------------------------------
        # Create streamer
        # ----------------------------------------------------

        streamer = (
            upstox_client.MarketDataStreamerV3(
                api_client
            )
        )

        self.streamer = streamer

        # ----------------------------------------------------
        # OPEN CALLBACK
        # ----------------------------------------------------

        def on_open():

            with self._lock:

                self.websocket_connected = True

                self.websocket_error = None

                self.websocket_connected_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

            self._publish({"type": "state", "state": self.get_state()})

            print()
            print("=" * 70)
            print("          UPSTOX WEBSOCKET CONNECTED")
            print("=" * 70)
            print()

            print(
                f"Instrument : {instrument_key}"
            )

            print(
                "Mode       : LTPC"
            )

            print()

            print(
                "Subscribing to instrument..."
            )

            streamer.subscribe(
                [instrument_key],
                "ltpc",
            )

            print(
                "Subscription successful."
            )

            print()

        # ----------------------------------------------------
        # MESSAGE CALLBACK
        # ----------------------------------------------------

        def on_message(message):

            try:

                with self._lock:

                    self.last_websocket_message_at = (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )

                self._process_websocket_message(
                    message=message,
                    instrument_key=instrument_key,
                )

            except Exception as exc:

                print()
                print(
                    "ERROR processing Upstox WebSocket "
                    "message:"
                )
                print(
                    f"{type(exc).__name__}: {exc}"
                )
                print()

                with self._lock:

                    self.websocket_error = (
                        f"{type(exc).__name__}: {exc}"
                    )

        # ----------------------------------------------------
        # ERROR CALLBACK
        # ----------------------------------------------------

        def on_error(error):

            print()
            print("=" * 70)
            print("             UPSTOX WEBSOCKET ERROR")
            print("=" * 70)
            print()
            print(error)
            print()

            with self._lock:

                self.websocket_connected = False

                self.websocket_error = str(error)

            self._publish({"type": "state", "state": self.get_state()})

        # ----------------------------------------------------
        # CLOSE CALLBACK
        # ----------------------------------------------------

        def on_close():

            print()
            print("=" * 70)
            print("            UPSTOX WEBSOCKET CLOSED")
            print("=" * 70)
            print()

            with self._lock:

                self.websocket_connected = False

            self._publish({"type": "state", "state": self.get_state()})

        # ----------------------------------------------------
        # RECONNECT CALLBACKS
        # ----------------------------------------------------

        def on_reconnecting(message=None):
            with self._lock:
                self.websocket_connected = False
                self.websocket_error = None
            self._publish({"type": "state", "state": self.get_state()})
            print("UPSTOX WEBSOCKET RECONNECTING...")

        def on_auto_reconnect_stopped(message=None):
            with self._lock:
                self.websocket_connected = False
                self.websocket_error = str(message or "Automatic reconnect attempts stopped.")
            self._publish({"type": "state", "state": self.get_state()})
            print("UPSTOX WEBSOCKET AUTO-RECONNECT STOPPED")

        # ----------------------------------------------------
        # Register callbacks
        # ----------------------------------------------------

        streamer.on(
            "open",
            on_open,
        )

        streamer.on(
            "message",
            on_message,
        )

        streamer.on(
            "error",
            on_error,
        )

        streamer.on(
            "close",
            on_close,
        )

        streamer.on(
            "reconnecting",
            on_reconnecting,
        )

        streamer.on(
            "autoReconnectStopped",
            on_auto_reconnect_stopped,
        )


        # ----------------------------------------------------
        # Enable automatic reconnect. Upstox supports configuring the
        # retry interval and retry count on MarketDataStreamerV3.
        streamer.auto_reconnect(True, 5, 20)

        # ----------------------------------------------------
        # Connect in background
        # ----------------------------------------------------

        def connect_streamer():

            try:

                print()
                print(
                    "Connecting to Upstox WebSocket..."
                )

                streamer.connect()

            except Exception as exc:

                print()
                print(
                    "ERROR connecting to Upstox:"
                )
                print(
                    f"{type(exc).__name__}: {exc}"
                )
                print()

                with self._lock:

                    self.websocket_connected = False

                    self.websocket_error = (
                        f"{type(exc).__name__}: {exc}"
                    )

        websocket_thread = threading.Thread(
            target=connect_streamer,
            name="UpstoxWebSocket",
            daemon=True,
        )

        self.websocket_thread = (
            websocket_thread
        )

        websocket_thread.start()

    # ========================================================
    # PROCESS WEBSOCKET MESSAGE
    # ========================================================

    def _process_websocket_message(
        self,
        message,
        instrument_key: str,
    ):

        if not isinstance(message, dict):
            return

        # ----------------------------------------------------
        # Ignore market information message
        # ----------------------------------------------------

        if message.get("type") == "market_info":

            print(
                "Upstox market information received."
            )

            return

        # ----------------------------------------------------
        # Get feeds
        # ----------------------------------------------------

        feeds = message.get(
            "feeds",
            {},
        )

        if not isinstance(feeds, dict):
            return

        instrument_feed = feeds.get(
            instrument_key
        )

        if not instrument_feed:
            return

        # ----------------------------------------------------
        # LTPC
        # ----------------------------------------------------

        ltpc = instrument_feed.get(
            "ltpc"
        )

        if not ltpc:
            return

        # ----------------------------------------------------
        # Extract values
        # ----------------------------------------------------

        ltp = ltpc.get(
            "ltp"
        )

        ltt = ltpc.get(
            "ltt"
        )
        

        ltq = ltpc.get(
            "ltq",
            0,
        )
        
        if ltp is None or ltt is None:
            return

        try:

            price = float(ltp)

            timestamp_ms = int(ltt)

            quantity = int(
                ltq or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            return

        # ----------------------------------------------------
        # Duplicate protection
        # ----------------------------------------------------

        current_event = (
            timestamp_ms,
            price,
            quantity,
        )

        with self._lock:

            if (
                current_event
                == self.last_ltp_event
            ):
                return

            self.last_ltp_event = (
                current_event
            )

        # ----------------------------------------------------
        # Store/process live tick
        # ----------------------------------------------------

        manager = self.manager

        if manager is None:

            print(
                "WARNING: LiveFeedManager "
                "is not available."
            )

            return

        print(
            f"LIVE | "
            f"Price: ₹{price:.2f} | "
            f"Qty: {quantity}"
        )

        completed = manager.process_tick(
            price=price,
            timestamp_ms=timestamp_ms,
            quantity=quantity,
        )

        self._publish({
            "type": "tick",
            "state": self.get_state(),
            "tick": self.get_latest_tick(),
            "current_candle": self.get_current_candle(),
            "completed_candles": list(completed.values()),
            "analysis": self.get_analysis(),
        })

    # ========================================================
    # BROWSER SUBSCRIBERS
    # ========================================================

    def subscribe(self, callback):
        with self._lock:
            self._subscribers.add(callback)

    def unsubscribe(self, callback):
        with self._lock:
            self._subscribers.discard(callback)

    def _publish(self, payload: dict):
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            try:
                callback(payload)
            except Exception as exc:
                print(f"LIVE CLIENT PUBLISH ERROR: {type(exc).__name__}: {exc}")

    def publish_snapshot(self):
        self._publish({
            "type": "snapshot",
            "state": self.get_state(),
            "candles": self.get_candles(),
            "current_candle": self.get_current_candle(),
            "analysis": self.get_analysis(),
        })

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        with self._lock:

            # ------------------------------------------------
            # Disconnect WebSocket
            # ------------------------------------------------

            if self.streamer is not None:

                try:

                    self.streamer.disconnect()

                except Exception:
                    pass

            # ------------------------------------------------
            # Stop manager
            # ------------------------------------------------

            if self.manager is not None:

                try:

                    self.manager.stop()

                except Exception:
                    pass

            # ------------------------------------------------
            # Reset state
            # ------------------------------------------------

            self.streamer = None
            self.websocket_thread = None

            self.manager = None

            self.websocket_connected = False

            self.websocket_error = None

            self.websocket_connected_at = None

            self.last_websocket_message_at = None

            self.last_ltp_event = None

            self.running = False

    # ========================================================
    # CHANGE INTERVAL
    # ========================================================

    def set_interval(
        self,
        interval: str,
    ):

        if interval not in self.SUPPORTED_INTERVALS:

            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported intervals: "
                f"{self.SUPPORTED_INTERVALS}"
            )

        with self._lock:

            if self.manager is None:

                raise RuntimeError(
                    "Live market feed is not running."
                )

            self.manager.set_interval(
                interval
            )

    # ========================================================
    # CANDLES
    # ========================================================

    def get_candles(self):

        with self._lock:

            if self.manager is None:
                return []

            return self.manager.get_candles()

    # ========================================================
    # DATAFRAME
    # ========================================================

    def get_dataframe(self):

        with self._lock:

            if self.manager is None:
                return None

            return self.manager.get_dataframe()

    # ========================================================
    # ANALYSIS
    # ========================================================

    def get_analysis(self):

        with self._lock:

            if self.manager is None:
                return None

            return (
                self.manager
                .get_latest_analysis()
            )

    # ========================================================
    # CURRENT CANDLE
    # ========================================================

    def get_current_candle(self):

        with self._lock:

            if self.manager is None:
                return None

            return (
                self.manager
                .get_current_candle()
            )

    # ========================================================
    # LATEST TICK
    # ========================================================

    def get_latest_tick(self):

        with self._lock:

            if self.manager is None:
                return None

            return (
                self.manager
                .get_latest_tick()
            )

    # ========================================================
    # STATE
    # ========================================================

    def get_state(self):

        with self._lock:

            if self.manager is None:

                return {
                    "running": False,
                    "instrument": self.instrument,
                    "interval": None,
                    "candles": 0,
                    "latest_tick": None,
                    "analysis_available": False,

                    # WebSocket
                    "websocket_connected": False,
                    "websocket_error": (
                        self.websocket_error
                    ),
                    "websocket_connected_at": (
                        self.websocket_connected_at
                    ),
                    "last_websocket_message_at": (
                        self.last_websocket_message_at
                    ),
                    "websocket_mode": "ltpc",
                }

            state = (
                self.manager.get_state()
            )

            state["instrument"] = (
                self.instrument
            )

            # ------------------------------------------------
            # WebSocket state
            # ------------------------------------------------

            state[
                "websocket_connected"
            ] = (
                self.websocket_connected
            )

            state[
                "websocket_error"
            ] = (
                self.websocket_error
            )

            state[
                "websocket_connected_at"
            ] = (
                self.websocket_connected_at
            )

            state[
                "last_websocket_message_at"
            ] = (
                self.last_websocket_message_at
            )

            state["websocket_mode"] = "ltpc"

            return state