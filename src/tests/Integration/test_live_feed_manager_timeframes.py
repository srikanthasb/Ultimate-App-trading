from src.services.live_feed_manager import LiveFeedManager


def print_header(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    print_header("LIVE FEED MANAGER - MULTI-TIMEFRAME TEST")

    manager = LiveFeedManager(
        symbol="TCS.NS",
        instrument_key="NSE_EQ|INE467B01029",
        max_candles=200,
    )

    print()
    print("Starting manager...")
    manager.start(interval="1m")

    print()
    print("Initial state:")
    print(manager.get_state())

    intervals = [
        "1m",
        "3m",
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    ]

    print_header("TESTING TIMEFRAME SWITCHING")

    for interval in intervals:
        print()
        print(f"Switching to: {interval}")

        manager.set_interval(interval)

        state = manager.get_state()

        print(f"Selected interval : {state['selected_interval']}")
        print(f"Expected interval  : {interval}")

        assert state["selected_interval"] == interval

        candles = manager.get_candles(interval)

        print(f"Candles available  : {len(candles)}")

        assert len(candles) > 0

        dataframe = manager.get_dataframe(interval)

        print(f"DataFrame rows      : {len(dataframe)}")

        assert not dataframe.empty

        print("Timeframe switch: PASS")

    print_header("VERIFYING DIFFERENT TIMEFRAME DATA")

    for interval in intervals:
        candles = manager.get_candles(interval)

        latest = candles[-1]

        print()
        print(f"{interval}:")
        print(f"  Candle timestamp : {latest['timestamp']}")
        print(f"  Open             : ₹{latest['open']:.2f}")
        print(f"  High             : ₹{latest['high']:.2f}")
        print(f"  Low              : ₹{latest['low']:.2f}")
        print(f"  Close            : ₹{latest['close']:.2f}")
        print(f"  Volume           : {latest['volume']}")

    print_header("VERIFYING MANAGER STATE")

    final_state = manager.get_state()

    print(final_state)

    assert final_state["running"] is True
    assert final_state["selected_interval"] == "1h"

    print()
    print("Final selected timeframe: PASS")
    print("Manager running: PASS")

    manager.stop()

    print()
    print("=" * 60)
    print("ALL MULTI-TIMEFRAME TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()