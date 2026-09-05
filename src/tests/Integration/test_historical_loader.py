from src.data.historical_candle_loader import (
    load_historical_candles,
)


SYMBOL = "TCS.NS"
INSTRUMENT_KEY = "NSE_EQ|INE467B01029"


INTERVALS = [
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
]


for interval in INTERVALS:

    print()
    print("=" * 70)
    print(
        f"TESTING {interval} HISTORICAL CANDLES"
    )
    print("=" * 70)

    try:

        store = load_historical_candles(
            symbol=SYMBOL,
            interval=interval,
            max_candles=200,
            instrument_key=INSTRUMENT_KEY,
        )

        print(
            f"Candles loaded : {store.count()}"
        )

        latest = store.get_latest()

        if latest:

            print(
                f"Latest candle : "
                f"{latest['timestamp']}"
            )

            print(
                f"Open          : "
                f"{latest['open']}"
            )

            print(
                f"High          : "
                f"{latest['high']}"
            )

            print(
                f"Low           : "
                f"{latest['low']}"
            )

            print(
                f"Close         : "
                f"{latest['close']}"
            )

            print(
                f"Volume        : "
                f"{latest['volume']}"
            )

        print("STATUS        : PASS")

    except Exception as error:

        print(
            f"STATUS        : FAIL"
        )

        print(
            f"ERROR         : {error}"
        )