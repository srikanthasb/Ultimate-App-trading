from src.data.live_candle_store import LiveCandleStore


def main():

    print()
    print("=" * 50)
    print("       LIVE CANDLE STORE TEST")
    print("=" * 50)

    store = LiveCandleStore(max_candles=3)

    candles = [
        {
            "symbol": "TCS.NS",
            "interval": "1m",
            "timestamp": "2026-08-31T09:15:00+05:30",
            "open": 2340.0,
            "high": 2345.0,
            "low": 2338.0,
            "close": 2345.0,
            "volume": 70,
        },
        {
            "symbol": "TCS.NS",
            "interval": "1m",
            "timestamp": "2026-08-31T09:16:00+05:30",
            "open": 2343.0,
            "high": 2348.0,
            "low": 2341.0,
            "close": 2347.0,
            "volume": 100,
        },
        {
            "symbol": "TCS.NS",
            "interval": "1m",
            "timestamp": "2026-08-31T09:17:00+05:30",
            "open": 2347.0,
            "high": 2350.0,
            "low": 2345.0,
            "close": 2349.0,
            "volume": 120,
        },
        {
            "symbol": "TCS.NS",
            "interval": "1m",
            "timestamp": "2026-08-31T09:18:00+05:30",
            "open": 2349.0,
            "high": 2352.0,
            "low": 2348.0,
            "close": 2351.0,
            "volume": 90,
        },
    ]

    print()
    print("Adding candles...")

    for candle in candles:
        store.add_candle(candle)

        print(
            f"Added: {candle['timestamp']} | "
            f"Close: ₹{candle['close']:.2f}"
        )

    print()
    print("===== STORE =====")

    print(f"Maximum candles : {store.max_candles}")
    print(f"Stored candles  : {store.count()}")

    print()
    print("===== DATAFRAME =====")

    dataframe = store.get_dataframe()

    print(dataframe)

    print()
    print("===== LATEST CANDLE =====")

    latest = store.get_latest()

    print(latest)

    print()
    print("=" * 50)
    print("      LIVE CANDLE STORE COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()