import os
import sys
import signal

import upstox_client
from dotenv import load_dotenv

from src.services.live_feed_manager import LiveFeedManager


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv(
    "UPSTOX_ACCESS_TOKEN"
)

MAX_CANDLES = 200

SUPPORTED_INTERVALS = [
    "1m",
    "3m",
    "5m",
    "10m",
    "15m",
    "30m",
    "1h",
]


# ============================================================
# DEFAULT INSTRUMENT
# ============================================================

DEFAULT_SYMBOL = "TCS"

DEFAULT_INSTRUMENT_KEY = (
    "NSE_EQ|INE467B01029"
)


# ============================================================
# GLOBAL OBJECTS
# ============================================================

manager = None
streamer = None

last_ltp_event = None

shutdown_started = False

symbol = None
instrument_key = None


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

def validate_configuration():

    if not UPSTOX_ACCESS_TOKEN:

        raise RuntimeError(
            "UPSTOX_ACCESS_TOKEN is missing from .env"
        )


# ============================================================
# COMMAND-LINE CONFIGURATION
# ============================================================

def get_configuration():

    """
    Command-line format:

        python -m src.data.upstox_live_feed

    Defaults:

        timeframe = 1m
        symbol = TCS
        instrument_key = NSE_EQ|INE467B01029


    Custom:

        python -m src.data.upstox_live_feed 3m TCS NSE_EQ|INE467B01029


    Example:

        python -m src.data.upstox_live_feed 5m RELIANCE NSE_EQ|XXXXXXXX
    """

    interval = "1m"

    selected_symbol = DEFAULT_SYMBOL

    selected_instrument_key = (
        DEFAULT_INSTRUMENT_KEY
    )

    # --------------------------------------------------------
    # TIMEFRAME
    # --------------------------------------------------------

    if len(sys.argv) >= 2:

        interval = sys.argv[1].strip()

    if interval not in SUPPORTED_INTERVALS:

        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported intervals: "
            f"{SUPPORTED_INTERVALS}"
        )

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    if len(sys.argv) >= 3:

        selected_symbol = (
            sys.argv[2].strip()
        )

    if not selected_symbol:

        raise ValueError(
            "Symbol cannot be empty."
        )

    # --------------------------------------------------------
    # INSTRUMENT KEY
    # --------------------------------------------------------

    if len(sys.argv) >= 4:

        selected_instrument_key = (
            sys.argv[3].strip()
        )

    if not selected_instrument_key:

        raise ValueError(
            "Instrument key cannot be empty."
        )

    return (
        interval,
        selected_symbol,
        selected_instrument_key,
    )


# ============================================================
# EXTRACT LTPC DATA
# ============================================================

def extract_ltpc(message):

    """
    Extract latest traded price information
    for the currently selected Upstox instrument.

    Returns:

        (price, timestamp_ms, quantity)

    or:

        None
    """

    if not isinstance(message, dict):

        return None

    # --------------------------------------------------------
    # MARKET INFORMATION
    # --------------------------------------------------------

    if message.get("type") == "market_info":

        print(
            "Market information received."
        )

        return None

    # --------------------------------------------------------
    # FEEDS
    # --------------------------------------------------------

    feeds = message.get(
        "feeds",
        {}
    )

    if not isinstance(feeds, dict):

        return None

    # --------------------------------------------------------
    # SELECTED INSTRUMENT
    # --------------------------------------------------------

    feed = feeds.get(
        instrument_key
    )

    if not isinstance(feed, dict):

        return None

    # --------------------------------------------------------
    # LTPC
    # --------------------------------------------------------

    ltpc = feed.get(
        "ltpc"
    )

    if not isinstance(ltpc, dict):

        return None

    price = ltpc.get(
        "ltp"
    )

    timestamp_ms = ltpc.get(
        "ltt"
    )

    quantity = ltpc.get(
        "ltq",
        0
    )

    if price is None:

        return None

    if timestamp_ms is None:

        return None

    # --------------------------------------------------------
    # CONVERT VALUES
    # --------------------------------------------------------

    try:

        price = float(price)

        timestamp_ms = int(
            timestamp_ms
        )

        quantity = int(
            quantity or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    return (
        price,
        timestamp_ms,
        quantity,
    )


# ============================================================
# PROCESS MARKET MESSAGE
# ============================================================

def process_market_message(message):

    global last_ltp_event

    result = extract_ltpc(
        message
    )

    if result is None:

        return

    price, timestamp_ms, quantity = (
        result
    )

    # --------------------------------------------------------
    # DUPLICATE EVENT PROTECTION
    # --------------------------------------------------------

    current_event = (
        timestamp_ms,
        price,
        quantity,
    )

    if current_event == last_ltp_event:

        return

    last_ltp_event = current_event

    # --------------------------------------------------------
    # MANAGER CHECK
    # --------------------------------------------------------

    if manager is None:

        return

    # --------------------------------------------------------
    # FORWARD LIVE TICK
    # --------------------------------------------------------

    try:

        manager.process_tick(
            price=price,
            timestamp_ms=timestamp_ms,
            quantity=quantity,
        )

    except Exception as exc:

        print()
        print(
            "ERROR while processing live tick:"
        )

        print(exc)


# ============================================================
# WEBSOCKET OPEN
# ============================================================

def on_open(*args):

    global streamer

    print()
    print("=" * 70)
    print("              UPSTOX LIVE MARKET FEED CONNECTED")
    print("=" * 70)
    print()

    print(
        f"Instrument      : {symbol}"
    )

    print(
        f"Instrument Key  : {instrument_key}"
    )

    print()

    # --------------------------------------------------------
    # SUBSCRIBE AFTER CONNECTION
    # --------------------------------------------------------

    try:

        print(
            "Subscribing to LTPC feed..."
        )

        streamer.subscribe(
            [
                instrument_key
            ],
            "ltpc",
        )

        print(
            "Subscription successful."
        )

    except Exception as exc:

        print()
        print(
            "ERROR while subscribing to Upstox:"
        )

        print(exc)

        print()

        try:

            streamer.disconnect()

        except Exception:

            pass

        raise

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    print()
    print(
        "Live market feed is now active."
    )

    print(
        "Waiting for live market ticks..."
    )

    print(
        "Press Ctrl+C to stop."
    )

    print()


# ============================================================
# WEBSOCKET MESSAGE
# ============================================================

def on_message(message):

    try:

        process_market_message(
            message
        )

    except Exception as exc:

        print()
        print(
            "ERROR in WebSocket message handler:"
        )

        print(exc)


# ============================================================
# WEBSOCKET ERROR
# ============================================================

def on_error(error):

    print()
    print("=" * 70)
    print("                 UPSTOX WEBSOCKET ERROR")
    print("=" * 70)
    print()

    print(error)

    print()
    print("=" * 70)


# ============================================================
# WEBSOCKET CLOSE
# ============================================================

def on_close(*args):

    print()
    print("=" * 70)
    print("              UPSTOX LIVE MARKET FEED CLOSED")
    print("=" * 70)
    print()


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown(
    signum=None,
    frame=None,
):

    global shutdown_started

    if shutdown_started:

        return

    shutdown_started = True

    print()
    print()
    print("=" * 70)
    print("                  SHUTDOWN REQUESTED")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # STOP LIVE FEED MANAGER
    # --------------------------------------------------------

    if manager is not None:

        try:

            manager.stop()

            print(
                "LiveFeedManager stopped."
            )

        except Exception as exc:

            print(
                "Error stopping LiveFeedManager:"
            )

            print(exc)

    # --------------------------------------------------------
    # DISCONNECT UPSTOX
    # --------------------------------------------------------

    if streamer is not None:

        try:

            streamer.disconnect()

            print(
                "Upstox WebSocket disconnected."
            )

        except Exception as exc:

            print(
                "Error disconnecting Upstox WebSocket:"
            )

            print(exc)

    # --------------------------------------------------------
    # FINAL MESSAGE
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("                    LIVE FEED STOPPED")
    print("=" * 70)
    print()

    raise SystemExit(0)


# ============================================================
# CREATE LIVE FEED MANAGER
# ============================================================

def create_manager(
    initial_interval,
):

    global manager

    print()
    print("=" * 70)
    print("                CREATING LIVE FEED MANAGER")
    print("=" * 70)
    print()

    manager = LiveFeedManager(
        symbol=symbol,
        instrument_key=instrument_key,
        max_candles=MAX_CANDLES,
    )

    print(
        f"Starting LiveFeedManager for {symbol}..."
    )

    manager.start(
        interval=initial_interval
    )

    print()
    print(
        "LiveFeedManager started successfully."
    )

    print()
    print(
        f"ACTIVE TIMEFRAME: {initial_interval}"
    )

    print()
    print(
        "Available timeframes:"
    )

    for interval in SUPPORTED_INTERVALS:

        print(
            f"  - {interval}"
        )

    print()


# ============================================================
# CREATE UPSTOX STREAMER
# ============================================================

def create_streamer():

    global streamer

    print()
    print("=" * 70)
    print("                 CREATING UPSTOX STREAMER")
    print("=" * 70)
    print()

    configuration = (
        upstox_client.Configuration()
    )

    configuration.access_token = (
        UPSTOX_ACCESS_TOKEN
    )

    api_client = (
        upstox_client.ApiClient(
            configuration
        )
    )

    streamer = (
        upstox_client.MarketDataStreamerV3(
            api_client
        )
    )

    print(
        "Upstox MarketDataStreamerV3 created."
    )

    return streamer


# ============================================================
# REGISTER CALLBACKS
# ============================================================

def register_callbacks():

    print()
    print(
        "Registering WebSocket callbacks..."
    )

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

    print(
        "WebSocket callbacks registered."
    )


# ============================================================
# START LIVE FEED
# ============================================================

def start_live_feed():

    global streamer

    initial_interval = (
        get_configuration()[0]
    )

    print()
    print("=" * 70)
    print("                 UPSTOX LIVE FEED")
    print("=" * 70)
    print()

    print(
        f"Symbol: {symbol}"
    )

    print(
        f"Instrument Key: {instrument_key}"
    )

    print(
        f"Initial timeframe: {initial_interval}"
    )

    print()

    # --------------------------------------------------------
    # VALIDATE ENVIRONMENT
    # --------------------------------------------------------

    validate_configuration()

    print(
        "Configuration validated."
    )

    # --------------------------------------------------------
    # CREATE MANAGER
    # --------------------------------------------------------

    create_manager(
        initial_interval
    )

    # --------------------------------------------------------
    # CREATE STREAMER
    # --------------------------------------------------------

    create_streamer()

    # --------------------------------------------------------
    # REGISTER CALLBACKS
    # --------------------------------------------------------

    register_callbacks()

    # --------------------------------------------------------
    # ENABLE AUTO RECONNECT
    # --------------------------------------------------------

    streamer.auto_reconnect(True, 5, 20)

    print()
    print(
        "Automatic WebSocket reconnect: ENABLED (5s / 20 attempts)"
    )

    # --------------------------------------------------------
    # CTRL+C
    # --------------------------------------------------------

    signal.signal(
        signal.SIGINT,
        shutdown,
    )

    print()
    print(
        "Ctrl+C shutdown handler registered."
    )

    # --------------------------------------------------------
    # CONNECT
    #
    # DO NOT SUBSCRIBE HERE.
    #
    # Subscription happens inside on_open().
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("                  CONNECTING TO UPSTOX")
    print("=" * 70)
    print()

    print(
        "Connecting to Upstox..."
    )

    try:

        streamer.connect()

    except KeyboardInterrupt:

        print()
        print(
            "KeyboardInterrupt received."
        )

        shutdown()

    except SystemExit:

        raise

    except Exception as exc:

        print()
        print("=" * 70)
        print("              UPSTOX CONNECTION FAILED")
        print("=" * 70)
        print()

        print(exc)

        print()

        if manager is not None:

            try:

                manager.stop()

                print(
                    "LiveFeedManager stopped."
                )

            except Exception as manager_exc:

                print(
                    "Error stopping LiveFeedManager:"
                )

                print(manager_exc)

        if streamer is not None:

            try:

                streamer.disconnect()

                print(
                    "Upstox WebSocket disconnected."
                )

            except Exception as streamer_exc:

                print(
                    "Error disconnecting WebSocket:"
                )

                print(streamer_exc)

        raise


# ============================================================
# MAIN
# ============================================================

def main():

    global symbol
    global instrument_key

    (
        initial_interval,
        selected_symbol,
        selected_instrument_key,
    ) = get_configuration()

    symbol = selected_symbol

    instrument_key = (
        selected_instrument_key
    )

    print()
    print("=" * 70)
    print("             UPSTOX LIVE TRADING GUIDANCE SYSTEM")
    print("=" * 70)
    print()

    print(
        "Data source:"
    )

    print(
        "  Upstox WebSocket"
    )

    print()

    print(
        "Symbol:"
    )

    print(
        f"  {symbol}"
    )

    print()

    print(
        "Instrument:"
    )

    print(
        f"  {instrument_key}"
    )

    print()

    print(
        "Initial timeframe:"
    )

    print(
        f"  {initial_interval}"
    )

    print()

    print(
        "Supported timeframes:"
    )

    for interval in SUPPORTED_INTERVALS:

        print(
            f"  - {interval}"
        )

    print()

    print(
        "Historical bootstrap:"
    )

    print(
        "  Upstox historical candles"
    )

    print()

    print(
        "Live feed:"
    )

    print(
        "  Upstox WebSocket"
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()

    start_live_feed()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()