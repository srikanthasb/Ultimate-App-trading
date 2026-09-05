import pandas as pd

from src.data.historical_candle_loader import load_historical_candles
from src.analysis.market_structure import find_recent_swing


def main():

    print("=" * 60)
    print("       MARKET STRUCTURE TEST")
    print("=" * 60)

    print()
    print("Loading historical candles...")

    store = load_historical_candles(
        symbol="TCS.NS",
        period="5d",
        interval="1m",
        max_candles=200,
        instrument_key="NSE_EQ|INE467B01029",
    )

    data = store.get_dataframe()

    print(f"Stored candles : {len(data)}")
    print(f"Latest candle  : {data.index[-1]}")
    print(f"Latest close   : ₹{data['Close'].iloc[-1]:.2f}")

    print()
    print("Finding recent confirmed swing points...")

    structure = find_recent_swing(
        data=data,
        lookback=2,
    )

    print()
    print("===== MARKET STRUCTURE =====")

    swing_high = structure["swing_high"]
    swing_low = structure["swing_low"]

    if swing_high:
        print(
            f"Swing High : ₹{swing_high['price']:.2f}"
        )
        print(
            f"High Time  : {swing_high['timestamp']}"
        )
    else:
        print("Swing High : None")

    print()

    if swing_low:
        print(
            f"Swing Low  : ₹{swing_low['price']:.2f}"
        )
        print(
            f"Low Time   : {swing_low['timestamp']}"
        )
    else:
        print("Swing Low  : None")

    print()
    print("=" * 60)
    print("     MARKET STRUCTURE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()