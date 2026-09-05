from datetime import datetime
from zoneinfo import ZoneInfo

from src.data.candle_engine import CandleEngine


IST = ZoneInfo("Asia/Kolkata")


def timestamp_ms(hour, minute, second):
    dt = datetime(
        2026,
        8,
        31,
        hour,
        minute,
        second,
        tzinfo=IST,
    )

    return int(dt.timestamp() * 1000)


def main():

    print()
    print("=" * 50)
    print("        CANDLE ENGINE TEST")
    print("=" * 50)
    print()

    engine = CandleEngine(
        symbol="TCS.NS",
        interval="1m",
    )

    ticks = [
        (2340.0, timestamp_ms(9, 15, 5), 10),
        (2342.0, timestamp_ms(9, 15, 15), 20),
        (2338.0, timestamp_ms(9, 15, 30), 15),
        (2345.0, timestamp_ms(9, 15, 55), 25),

        # New minute
        (2343.0, timestamp_ms(9, 16, 5), 12),
    ]

    for price, timestamp, quantity in ticks:

        completed = engine.update(
            price=price,
            timestamp_ms=timestamp,
            quantity=quantity,
        )

        print(
            f"Tick -> Price: {price}, "
            f"Quantity: {quantity}"
        )

        if completed:
            print()
            print("===== COMPLETED CANDLE =====")
            print(f"Symbol : {completed['symbol']}")
            print(f"Time   : {completed['timestamp']}")
            print(f"Open   : {completed['open']}")
            print(f"High   : {completed['high']}")
            print(f"Low    : {completed['low']}")
            print(f"Close  : {completed['close']}")
            print(f"Volume : {completed['volume']}")
            print()

    print("===== CURRENT CANDLE =====")

    current = engine.get_current_candle()

    print(f"Symbol : {current['symbol']}")
    print(f"Time   : {current['timestamp']}")
    print(f"Open   : {current['open']}")
    print(f"High   : {current['high']}")
    print(f"Low    : {current['low']}")
    print(f"Close  : {current['close']}")
    print(f"Volume : {current['volume']}")

    print()
    print("=" * 50)
    print("       CANDLE ENGINE COMPLETE")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()