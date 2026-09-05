from src.services.live_feed_manager import LiveFeedManager


def main():
    print("=" * 60)
    print("LIVE FEED MANAGER TEST")
    print("=" * 60)

    manager = LiveFeedManager(
        symbol="TCS.NS",
        instrument_key="NSE_EQ|INE467B01029",
        max_candles=200,
    )

    print("\nStarting manager...")

    manager.start("1m")

    print("\nManager started successfully.")

    print("\nCANDLE COUNTS")
    print("-" * 40)

    for interval in manager.SUPPORTED_INTERVALS:
        count = len(manager.get_candles(interval))
        print(f"{interval:>4}: {count}")

    print("\nSTATE")
    print("-" * 40)
    print(manager.get_state())

    manager.stop()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()