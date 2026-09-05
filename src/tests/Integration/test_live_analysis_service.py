from datetime import datetime, timedelta

from src.services.live_analysis_service import LiveAnalysisService


def main():
    print()
    print("=" * 60)
    print("       LIVE ANALYSIS SERVICE TEST")
    print("=" * 60)
    print()

    # Simulated completed 1-minute candles.
    #
    # We need enough candles for SMA50 and the other indicators.
    # These are deliberately generated as a simple historical sequence
    # so that the service can be tested without connecting to Upstox.

    candles = []

    base_price = 2300.0

    start_time = datetime.fromisoformat(
        "2026-08-31T09:15:00+05:30"
    )

    for i in range(60):
        price = base_price + (i * 2)

        candle_time = start_time + timedelta(minutes=i)

        candles.append(
            {
                "symbol": "TCS.NS",
                "interval": "1m",
                "timestamp": candle_time.isoformat(),
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + 1,
                "volume": 100 + i,
            }
        )

    print(f"Input candles : {len(candles)}")
    print()

    service = LiveAnalysisService()

    result = service.analyze(candles)

    snapshot = result["snapshot"]
    technical = result["technical_signal"]
    ai = result["ai_analysis"]
    decision = result["decision"]
    risk = result["risk"]

    print("===== MARKET SNAPSHOT =====")
    print(f"Symbol : {snapshot['symbol']}")
    print(f"Date   : {snapshot['date']}")
    print(f"Price  : {snapshot['price']}")
    print()

    print("===== TECHNICAL ANALYSIS =====")
    print(f"Trend      : {technical['trend']}")
    print(f"Signal     : {technical['signal']}")
    print(
        f"Alignment  : "
        f"{technical['technical_alignment']}%"
    )
    print(
        f"Bullish    : "
        f"{technical['bullish_points']}"
    )
    print(
        f"Bearish    : "
        f"{technical['bearish_points']}"
    )
    print()

    print("===== AI ANALYSIS =====")
    print(f"Trend      : {ai['trend']}")
    print(f"Momentum   : {ai['momentum']}")
    print(f"Signal     : {ai['signal']}")
    print(f"Confidence : {ai['confidence']}%")
    print()

    print("===== DECISION ENGINE =====")
    print(f"Final Signal : {decision['final_signal']}")
    print(f"Trend        : {decision['trend']}")
    print(f"Momentum     : {decision['momentum']}")
    print(f"Agreement    : {decision['agreement']}")
    print(
        f"Technical    : "
        f"{decision['technical_alignment']}%"
    )
    print(
        f"AI Confidence: "
        f"{decision['ai_confidence']}%"
    )
    print()

    print("===== RISK ENGINE =====")
    print(f"Risk       : {risk['risk']}")
    print(f"Risk Score : {risk['risk_score']}")
    print()

    print("Reasons:")

    for reason in risk["reasons"]:
        print(f" - {reason}")

    print()
    print("=" * 60)
    print("      LIVE ANALYSIS SERVICE COMPLETE")
    print("=" * 60)
    print()

    trade_plan = result["trade_plan"]

    print("===== TRADE PLAN =====")
    print(f"Signal          : {trade_plan['signal']}")
    print(f"Entry           : ₹{trade_plan['entry']}")
    print(f"ATR             : ₹{trade_plan['atr']}")
    print(f"ATR Buffer      : ₹{trade_plan['atr_buffer']}")
    print(f"Swing High      : ₹{trade_plan['swing_high']}")
    print(f"Swing Low       : ₹{trade_plan['swing_low']}")
    print(f"Stop Loss       : ₹{trade_plan['stop_loss']}")
    print(f"Target 1        : ₹{trade_plan['target_1']}")
    print(f"Target 2        : ₹{trade_plan['target_2']}")
    print(f"Risk / Share    : ₹{trade_plan['risk_per_share']}")
    print(f"Position Size   : {trade_plan['position_size']}")
    print(f"Trailing Stop   : ₹{trade_plan['trailing_stop']}")
    print(f"Structure Valid : {trade_plan['structure_valid']}")


if __name__ == "__main__":
    main()