from datetime import datetime
from zoneinfo import ZoneInfo

from src.data.candle_engine import CandleEngine


IST = ZoneInfo("Asia/Kolkata")


def timestamp_ms(hour, minute, second=0):
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


def test_interval(interval, hour, minute, expected):
    engine = CandleEngine(
        symbol="TCS.NS",
        interval=interval,
    )

    timestamp = timestamp_ms(hour, minute)

    bucket = engine._get_bucket_start(timestamp)

    actual = bucket.strftime("%H:%M")

    print(
        f"{interval:>4} | "
        f"tick {hour:02d}:{minute:02d} | "
        f"bucket {actual} | "
        f"expected {expected}"
    )

    assert actual == expected


def main():

    print("=" * 60)
    print("CANDLE ENGINE - NSE TIMEFRAME ALIGNMENT TEST")
    print("=" * 60)

    print()

    test_interval("1m", 9, 17, "09:17")
    test_interval("3m", 9, 19, "09:18")
    test_interval("5m", 9, 23, "09:20")
    test_interval("10m", 9, 32, "09:25")
    test_interval("15m", 9, 41, "09:30")
    test_interval("30m", 10, 2, "09:45")
    test_interval("1h", 10, 2, "09:15")

    print()
    print("=" * 60)
    print("ALL CANDLE ALIGNMENT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()