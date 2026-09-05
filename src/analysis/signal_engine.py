from src.analysis.strategy_engine import evaluate_strategies


def generate_signal(snapshot: dict) -> dict:
    """Generate a deterministic multi-strategy technical signal.

    The engine uses confluence across trend, momentum, volatility, volume,
    VWAP and market-structure inputs.  A trade is produced only when the
    directional evidence has a meaningful edge; otherwise the result is HOLD.
    """
    if not snapshot:
        raise ValueError("Market snapshot is empty.")

    result = evaluate_strategies(snapshot)
    buy_score = result["bullish_score"]
    sell_score = result["bearish_score"]

    reasons = [
        f"{item['name']}: {item['reason']}"
        for item in result["strategies"]
        if item["signal"] != "NEUTRAL"
    ]

    # Backward-compatible point counts for the existing UI/tests.
    bullish_points = sum(1 for item in result["strategies"] if item["signal"] == "BUY")
    bearish_points = sum(1 for item in result["strategies"] if item["signal"] == "SELL")

    return {
        "symbol": snapshot["symbol"],
        "signal": result["signal"],
        "trend": result["trend"],
        "technical_alignment": result["technical_alignment"],
        "bullish_points": bullish_points,
        "bearish_points": bearish_points,
        "bullish_score": buy_score,
        "bearish_score": sell_score,
        "strategy_count": result["strategy_count"],
        "strategies": result["strategies"],
        "reasons": reasons,
    }
