from src.data.market_data import get_market_data
from src.analysis.indicators import add_indicators
from src.analysis.snapshot import create_market_snapshot
from src.analysis.signal_engine import generate_signal
from src.analysis.ai_analyst import AIAnalyst
from src.analysis.decision_engine import make_decision


def main():

    symbol = "TCS.NS"

    print("\n========================================")
    print("       DECISION ENGINE TEST")
    print("========================================")

    # Market data
    data = get_market_data(
        ticker=symbol,
        period="6mo",
        interval="1d",
    )

    # Indicators
    data = add_indicators(data)
    data = data.dropna()

    # Snapshot
    snapshot = create_market_snapshot(
        data=data,
        symbol=symbol,
    )

    # Technical analysis
    technical_signal = generate_signal(snapshot)

    # AI analysis
    analyst = AIAnalyst()
    ai_analysis = analyst.analyze(snapshot)

    # Decision Engine
    decision = make_decision(
        snapshot=snapshot,
        technical_signal=technical_signal,
        ai_analysis=ai_analysis,
    )

    print("\n===== TECHNICAL ANALYSIS =====")
    print(f"Signal     : {technical_signal['signal']}")
    print(f"Alignment  : {technical_signal['technical_alignment']}%")

    print("\n===== AI ANALYSIS =====")
    print(f"Signal     : {ai_analysis['signal']}")
    print(f"Confidence : {ai_analysis['confidence']}%")

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
    print("      DECISION ENGINE COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()