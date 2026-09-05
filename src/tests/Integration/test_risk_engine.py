from src.analysis.risk_engine import calculate_risk


def main():

    technical_signal = {
        "symbol": "TCS.NS",
        "signal": "SELL",
        "trend": "Bearish",
        "technical_alignment": 83,
        "bullish_points": 1,
        "bearish_points": 5,
        "reasons": [
            "Price is below SMA20.",
            "Price is above SMA50.",
            "Price is below EMA20.",
            "RSI is below 50.",
            "MACD is below its signal line.",
            "MACD histogram is negative.",
        ],
    }

    ai_analysis = {
        "symbol": "TCS.NS",
        "trend": "Bearish",
        "momentum": "Negative",
        "signal": "SELL",
        "confidence": 70,
    }

    decision = {
        "symbol": "TCS.NS",
        "final_signal": "SELL",
        "trend": "Bearish",
        "momentum": "Negative",
        "agreement": True,
        "technical_alignment": 83,
        "ai_confidence": 70,
    }

    result = calculate_risk(
        technical_signal=technical_signal,
        ai_analysis=ai_analysis,
        decision=decision,
    )

    print()
    print("========================================")
    print("          RISK ENGINE TEST")
    print("========================================")

    print()
    print("===== INPUT =====")
    print(f"Final Signal       : {decision['final_signal']}")
    print(f"Technical Alignment: {technical_signal['technical_alignment']}%")
    print(f"AI Confidence      : {ai_analysis['confidence']}%")
    print(f"Agreement          : {decision['agreement']}")

    print()
    print("===== RISK ENGINE =====")
    print(f"Risk       : {result['risk']}")
    print(f"Risk Score : {result['risk_score']}")

    print()
    print("Reasons:")

    for reason in result["reasons"]:
        print(f" - {reason}")

    print()
    print("========================================")
    print("        RISK ENGINE COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()