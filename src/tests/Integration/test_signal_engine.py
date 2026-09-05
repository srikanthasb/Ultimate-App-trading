from src.analysis.signal_engine import generate_signal


snapshot = {
    "symbol": "TCS.NS",
    "date": "2026-08-27",
    "price": 3421.50,
    "open": 3398.00,
    "high": 3440.00,
    "low": 3385.00,
    "volume": 1250000,

    "sma_20": 3380.00,
    "sma_50": 3295.00,
    "ema_20": 3405.00,

    "rsi_14": 62.4,

    "macd": 18.2,
    "macd_signal": 14.7,
    "macd_histogram": 3.5,
}


def main():

    result = generate_signal(snapshot)

    print("\n===== TECHNICAL SIGNAL =====")
    print(f"Symbol          : {result['symbol']}")
    print(f"Trend           : {result['trend']}")
    print(f"Signal          : {result['signal']}")
    print(f"technical_alignment : {result['technical_alignment']}%")
    print(f"Bullish points  : {result['bullish_points']}")
    print(f"Bearish points  : {result['bearish_points']}")

    print("\nReasons:")

    for reason in result["reasons"]:
        print(f" - {reason}")


if __name__ == "__main__":
    main()