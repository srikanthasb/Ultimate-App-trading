from src.data.historical_candle_loader import (
    load_historical_candles,
)


def main():

    print()
    print("=" * 60)
    print("       HISTORICAL CANDLE LOADER TEST")
    print("=" * 60)

    print()
    print("Loading historical 1-minute candles...")

    store = load_historical_candles(
        symbol="TCS.NS",
        interval="1m",
        period="5d",
        max_candles=200,
        instrument_key="NSE_EQ|INE467B01029",
    )

    print()
    print("===== RESULT =====")

    print(
        f"Stored candles : {store.count()}"
    )

    print()

    latest = store.get_latest()

    print("===== LATEST CANDLE =====")

    print(latest)

    print()

    print("===== DATAFRAME =====")

    print(
        store.get_dataframe().tail()
    )

    print()
    print("=" * 60)
    print("   HISTORICAL CANDLE LOADER COMPLETE")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()