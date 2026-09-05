from datetime import datetime
from zoneinfo import ZoneInfo

from src.services.live_feed_manager import LiveFeedManager


IST = ZoneInfo("Asia/Kolkata")


def make_timestamp(hour: int, minute: int, second: int) -> int:
    """
    Create an IST timestamp in milliseconds.
    """
    dt = datetime(
        2026,
        9,
        1,
        hour,
        minute,
        second,
        tzinfo=IST,
    )

    return int(dt.timestamp() * 1000)


def print_candle(title: str, candle: dict | None):
    print()
    print(title)
    print("-" * 50)

    if candle is None:
        print("None")
        return

    for key, value in candle.items():
        print(f"{key:>10}: {value}")


def main():

    print("=" * 60)
    print("LIVE FEED MANAGER - TICK PROCESSING TEST")
    print("=" * 60)

    manager = LiveFeedManager(
        symbol="TCS.NS",
        instrument_key="NSE_EQ|INE467B01029",
        max_candles=200,
    )

    # ---------------------------------------------------------
    # 1. START MANAGER
    # ---------------------------------------------------------

    print("\nStarting manager...")

    manager.start("1m")

    print("Manager started.")

    # ---------------------------------------------------------
    # 2. SEND FIRST TICK
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 1 - FIRST TICK")
    print("=" * 60)

    tick_1 = {
        "symbol": "TCS.NS",
        "price": 2356.00,
        "timestamp": make_timestamp(15, 29, 10),
        "quantity": 100,
    }

    manager.process_tick(
        price=tick_1["price"],
        timestamp_ms=tick_1["timestamp"],
        quantity=tick_1["quantity"],
    )

    latest_tick = manager.get_latest_tick()
    current_candle = manager.get_current_candle("1m")

    print("\nLatest tick:")
    print(latest_tick)

    print_candle(
        "Current 1m candle after first tick:",
        current_candle,
    )

    # ---------------------------------------------------------
    # 3. SEND MORE TICKS IN SAME MINUTE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 2 - MULTIPLE TICKS IN SAME CANDLE")
    print("=" * 60)

    ticks = [
        {
            "symbol": "TCS.NS",
            "price": 2358.00,
            "timestamp": make_timestamp(15, 29, 20),
            "quantity": 200,
        },
        {
            "symbol": "TCS.NS",
            "price": 2354.00,
            "timestamp": make_timestamp(15, 29, 30),
            "quantity": 150,
        },
        {
            "symbol": "TCS.NS",
            "price": 2357.00,
            "timestamp": make_timestamp(15, 29, 45),
            "quantity": 250,
        },
    ]

    for tick in ticks:
        manager.process_tick(
            price=tick["price"],
            timestamp_ms=tick["timestamp"],
            quantity=tick["quantity"],
        )

    current_candle = manager.get_current_candle("1m")

    print_candle(
        "Current 1m candle after multiple ticks:",
        current_candle,
    )

    # ---------------------------------------------------------
    # 4. VERIFY OHLC
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 3 - VERIFY OHLCV")
    print("=" * 60)

    expected_open = 2356.00
    expected_high = 2358.00
    expected_low = 2354.00
    expected_close = 2357.00
    expected_volume = 100 + 200 + 150 + 250

    assert current_candle["open"] == expected_open
    assert current_candle["high"] == expected_high
    assert current_candle["low"] == expected_low
    assert current_candle["close"] == expected_close
    assert current_candle["volume"] == expected_volume

    print("OPEN   :", current_candle["open"], "PASS")
    print("HIGH   :", current_candle["high"], "PASS")
    print("LOW    :", current_candle["low"], "PASS")
    print("CLOSE  :", current_candle["close"], "PASS")
    print("VOLUME :", current_candle["volume"], "PASS")

    # ---------------------------------------------------------
    # 5. NO COMPLETED CANDLE YET
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 4 - CANDLE SHOULD STILL BE FORMING")
    print("=" * 60)

    completed = manager.get_latest_completed_candle("1m")

    print_candle(
        "Latest completed 1m candle:",
        completed,
    )

    # We have only sent ticks inside 15:29.
    # Therefore the 09:15 candle should still be forming.
    assert manager.get_current_candle("1m") is not None

    print("\nCurrent candle still forming: PASS")

    # ---------------------------------------------------------
    # 6. MOVE INTO NEXT MINUTE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 5 - NEW MINUTE")
    print("=" * 60)

    next_tick = {
        "symbol": "TCS.NS",
        "price": 2360.00,
        "timestamp": make_timestamp(15, 30, 5),
        "quantity": 300,
    }

    manager.process_tick(
        price=next_tick["price"],
        timestamp_ms=next_tick["timestamp"],
        quantity=next_tick["quantity"],
    )

    completed = manager.get_latest_completed_candle("1m")
    current_candle = manager.get_current_candle("1m")

    print_candle(
        "Completed 1m candle:",
        completed,
    )

    print_candle(
        "New current 1m candle:",
        current_candle,
    )

    # ---------------------------------------------------------
    # 7. VERIFY COMPLETED CANDLE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 6 - VERIFY COMPLETED CANDLE")
    print("=" * 60)

    assert completed is not None

    assert completed["open"] == 2356.00
    assert completed["high"] == 2358.00
    assert completed["low"] == 2354.00
    assert completed["close"] == 2357.00
    assert completed["volume"] == 700

    print("Completed candle OPEN   : PASS")
    print("Completed candle HIGH   : PASS")
    print("Completed candle LOW    : PASS")
    print("Completed candle CLOSE  : PASS")
    print("Completed candle VOLUME : PASS")

    # ---------------------------------------------------------
    # 8. VERIFY NEW CURRENT CANDLE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 7 - VERIFY NEW CURRENT CANDLE")
    print("=" * 60)

    assert current_candle is not None
    assert current_candle["open"] == 2360.00
    assert current_candle["high"] == 2360.00
    assert current_candle["low"] == 2360.00
    assert current_candle["close"] == 2360.00
    assert current_candle["volume"] == 300

    print("New candle OPEN   : PASS")
    print("New candle HIGH   : PASS")
    print("New candle LOW    : PASS")
    print("New candle CLOSE  : PASS")
    print("New candle VOLUME : PASS")

    # ---------------------------------------------------------
    # 9. VERIFY STORE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 8 - VERIFY CANDLE STORE")
    print("=" * 60)

    candles = manager.get_candles("1m")

    print(f"1m candles currently stored: {len(candles)}")

    assert len(candles) > 0

    print("1m candle store: PASS")

    # ---------------------------------------------------------
    # 10. VERIFY LATEST TICK
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST 9 - VERIFY LATEST TICK")
    print("=" * 60)

    latest_tick = manager.get_latest_tick()

    print("Latest tick:")
    print(latest_tick)

    assert latest_tick is not None
    assert latest_tick["price"] == 2360.00
    assert latest_tick["quantity"] == 300

    print("Latest tick: PASS")

    # ---------------------------------------------------------
    # 11. STATE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("FINAL MANAGER STATE")
    print("=" * 60)

    print(manager.get_state())

    # ---------------------------------------------------------
    # 12. STOP
    # ---------------------------------------------------------

    manager.stop()

    print("\n" + "=" * 60)
    print("ALL TICK-PROCESSING TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()