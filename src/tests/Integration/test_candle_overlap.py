from src.data.live_candle_store import LiveCandleStore


def make_candle(timestamp, close):
    return {
        "symbol": "TCS.NS",
        "interval": "1m",
        "timestamp": timestamp,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 100,
    }


def main():

    print()
    print("=" * 60)
    print("       CANDLE OVERLAP PROTECTION TEST")
    print("=" * 60)

    store = LiveCandleStore(max_candles=5)

    # Historical candles
    historical = [
        make_candle("2026-09-01T12:49:00+05:30", 2360),
        make_candle("2026-09-01T12:50:00+05:30", 2361),
        make_candle("2026-09-01T12:51:00+05:30", 2362),
    ]

    for candle in historical:
        store.add_candle(candle)

    print()
    print("Historical candles loaded :", store.count())
    print("Latest:", store.get_latest()["timestamp"])

    # Simulate overlapping live candle
    overlapping = make_candle(
        "2026-09-01T12:51:00+05:30",
        2365,
    )

    store.add_candle(overlapping)

    print()
    print("After overlapping candle :", store.count())
    print("Latest:", store.get_latest()["timestamp"])
    print("Latest close:", store.get_latest()["close"])

    # Simulate new live candle
    new_live = make_candle(
        "2026-09-01T12:52:00+05:30",
        2366,
    )

    store.add_candle(new_live)

    print()
    print("After new live candle    :", store.count())
    print("Latest:", store.get_latest()["timestamp"])
    print("Latest close:", store.get_latest()["close"])

    print()
    print("=" * 60)
    print("       CANDLE OVERLAP TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()