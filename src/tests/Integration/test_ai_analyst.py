import os

from dotenv import load_dotenv
from src.analysis.ai_analyst import AIAnalyst

load_dotenv()

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
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    analyst = AIAnalyst()

    result = analyst.analyze(snapshot)

    print("\n===== AI MARKET ANALYSIS =====")
    print(f"Symbol     : {result['symbol']}")
    print(f"Trend      : {result['trend']}")
    print(f"Momentum   : {result['momentum']}")
    print(f"Signal     : {result['signal']}")
    print(f"Confidence : {result['confidence']}%")
    print(f"Summary    : {result['summary']}")

    print("\nReasons:")
    for reason in result["reasons"]:
        print(f" - {reason}")


if __name__ == "__main__":
    main()