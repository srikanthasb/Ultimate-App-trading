from src.services.analysis_service import AnalysisService


def main():

    symbol = "TCS.NS"

    print("\n========================================")
    print("        ANALYSIS SERVICE TEST")
    print("========================================")

    service = AnalysisService()

    result = service.analyze(symbol)

    snapshot = result["snapshot"]
    technical = result["technical_signal"]
    ai = result["ai_analysis"]
    decision = result["decision"]

    print("\n===== MARKET SNAPSHOT =====")
    print(f"Symbol : {snapshot['symbol']}")
    print(f"Date   : {snapshot['date']}")
    print(f"Price  : {snapshot['price']}")

    print("\n===== TECHNICAL ANALYSIS =====")
    print(f"Trend      : {technical['trend']}")
    print(f"Signal     : {technical['signal']}")
    print(f"Alignment : {technical['technical_alignment']}%")
    print(f"Bullish    : {technical['bullish_points']}")
    print(f"Bearish    : {technical['bearish_points']}")

    print("\n===== AI ANALYSIS =====")
    print(f"Trend      : {ai['trend']}")
    print(f"Momentum   : {ai['momentum']}")
    print(f"Signal     : {ai['signal']}")
    print(f"Confidence : {ai['confidence']}%")

    print("\nSummary:")
    print(ai["summary"])

    print("\n===== DECISION ENGINE =====")
    print(f"Final Signal : {decision['final_signal']}")
    print(f"Trend        : {decision['trend']}")
    print(f"Momentum     : {decision['momentum']}")
    print(f"Agreement    : {decision['agreement']}")
    print(f"Technical    : {decision['technical_alignment']}%")
    print(f"AI Confidence: {decision['ai_confidence']}%")
    print(f"Risk         : {decision['risk']}")

    print("\nExplanation:")
    print(decision["explanation"])

    print("\n========================================")
    print("       ANALYSIS SERVICE COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()