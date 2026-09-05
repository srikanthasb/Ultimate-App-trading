from __future__ import annotations

from typing import Any


def _number(snapshot: dict, key: str):
    value = snapshot.get(key)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def evaluate_strategies(snapshot: dict) -> dict:
    """Evaluate independent technical strategies from one verified snapshot.

    The engine is deliberately deterministic.  It provides confluence rather
    than pretending that any single indicator can guarantee a profitable trade.
    """
    price = _number(snapshot, "price")
    if price is None:
        raise ValueError("Snapshot price is missing.")

    scores = {"BUY": 0.0, "SELL": 0.0}
    strategies: list[dict[str, Any]] = []

    def add(name: str, direction: str | None, weight: float, reason: str):
        if direction in scores:
            scores[direction] += weight
        strategies.append({
            "name": name,
            "signal": direction or "NEUTRAL",
            "weight": weight,
            "reason": reason,
        })

    # 1. Moving-average trend structure
    ema20, ema50 = _number(snapshot, "ema_20"), _number(snapshot, "ema_50")
    sma20, sma50 = _number(snapshot, "sma_20"), _number(snapshot, "sma_50")
    if all(v is not None for v in (ema20, ema50, sma20, sma50)):
        if price > ema20 > ema50 and sma20 > sma50:
            add("MA trend alignment", "BUY", 2.0, "Price and fast averages are aligned above slower averages.")
        elif price < ema20 < ema50 and sma20 < sma50:
            add("MA trend alignment", "SELL", 2.0, "Price and fast averages are aligned below slower averages.")
        else:
            add("MA trend alignment", None, 2.0, "Moving averages are not fully aligned.")

    # 2. RSI regime
    rsi = _number(snapshot, "rsi_14")
    if rsi is not None:
        if 55 <= rsi < 70:
            add("RSI momentum", "BUY", 1.0, f"RSI {rsi:.1f} confirms bullish momentum without being overbought.")
        elif 30 < rsi <= 45:
            add("RSI momentum", "SELL", 1.0, f"RSI {rsi:.1f} confirms bearish momentum without being oversold.")
        elif rsi >= 70:
            add("RSI regime", None, 1.0, f"RSI {rsi:.1f} is overbought; avoid chasing longs.")
        elif rsi <= 30:
            add("RSI regime", None, 1.0, f"RSI {rsi:.1f} is oversold; avoid chasing shorts.")
        else:
            add("RSI regime", None, 1.0, f"RSI {rsi:.1f} is in a neutral zone.")

    # 3. MACD momentum
    macd = _number(snapshot, "macd")
    macd_signal = _number(snapshot, "macd_signal")
    hist = _number(snapshot, "macd_histogram")
    if all(v is not None for v in (macd, macd_signal, hist)):
        if macd > macd_signal and hist > 0:
            add("MACD momentum", "BUY", 1.5, "MACD is above its signal and histogram is positive.")
        elif macd < macd_signal and hist < 0:
            add("MACD momentum", "SELL", 1.5, "MACD is below its signal and histogram is negative.")
        else:
            add("MACD momentum", None, 1.5, "MACD does not provide clean directional confirmation.")

    # 4. Bollinger position
    bb_mid = _number(snapshot, "bb_mavg")
    bb_high = _number(snapshot, "bb_high")
    bb_low = _number(snapshot, "bb_low")
    if all(v is not None for v in (bb_mid, bb_high, bb_low)) and bb_high > bb_low:
        if price > bb_mid and price < bb_high:
            add("Bollinger trend", "BUY", 1.0, "Price is above the Bollinger midline without breaking the upper band.")
        elif price < bb_mid and price > bb_low:
            add("Bollinger trend", "SELL", 1.0, "Price is below the Bollinger midline without breaking the lower band.")
        else:
            add("Bollinger position", None, 1.0, "Price is near an outer Bollinger band; confirmation is preferred.")

    # 5. Stochastic momentum
    stoch_k = _number(snapshot, "stoch_k")
    stoch_d = _number(snapshot, "stoch_d")
    if stoch_k is not None and stoch_d is not None:
        if stoch_k > stoch_d and stoch_k < 80:
            add("Stochastic momentum", "BUY", 1.0, "Stochastic K is above D without being overbought.")
        elif stoch_k < stoch_d and stoch_k > 20:
            add("Stochastic momentum", "SELL", 1.0, "Stochastic K is below D without being oversold.")
        else:
            add("Stochastic regime", None, 1.0, "Stochastic is at an extreme or lacks crossover confirmation.")

    # 6. ADX directional trend strength
    adx = _number(snapshot, "adx_14")
    plus_di = _number(snapshot, "plus_di")
    minus_di = _number(snapshot, "minus_di")
    if all(v is not None for v in (adx, plus_di, minus_di)):
        if adx >= 20 and plus_di > minus_di:
            add("ADX trend strength", "BUY", 1.5, f"ADX {adx:.1f} confirms a meaningful trend with +DI dominant.")
        elif adx >= 20 and minus_di > plus_di:
            add("ADX trend strength", "SELL", 1.5, f"ADX {adx:.1f} confirms a meaningful trend with -DI dominant.")
        else:
            add("ADX trend strength", None, 1.5, f"ADX {adx:.1f} does not confirm a strong directional trend.")

    # 7. VWAP
    vwap = _number(snapshot, "vwap")
    if vwap is not None:
        if price > vwap:
            add("VWAP bias", "BUY", 1.0, "Price is above session VWAP.")
        elif price < vwap:
            add("VWAP bias", "SELL", 1.0, "Price is below session VWAP.")
        else:
            add("VWAP bias", None, 1.0, "Price is at VWAP.")

    # 8. Volume / OBV confirmation
    volume_ratio = _number(snapshot, "volume_ratio")
    obv_slope = _number(snapshot, "obv_slope")
    if volume_ratio is not None and obv_slope is not None:
        if volume_ratio >= 1.0 and obv_slope > 0:
            add("Volume confirmation", "BUY", 1.0, "Volume is active and OBV is rising.")
        elif volume_ratio >= 1.0 and obv_slope < 0:
            add("Volume confirmation", "SELL", 1.0, "Volume is active and OBV is falling.")
        else:
            add("Volume confirmation", None, 1.0, "Volume does not confirm directional pressure.")

    # 9. CCI
    cci = _number(snapshot, "cci_20")
    if cci is not None:
        if cci > 100:
            add("CCI trend", "BUY", 0.75, f"CCI {cci:.1f} shows strong positive price pressure.")
        elif cci < -100:
            add("CCI trend", "SELL", 0.75, f"CCI {cci:.1f} shows strong negative price pressure.")
        else:
            add("CCI regime", None, 0.75, f"CCI {cci:.1f} is not at a strong trend threshold.")

    # 10. Williams %R
    willr = _number(snapshot, "williams_r")
    if willr is not None:
        if -80 < willr < -20 and willr > -50:
            add("Williams %R", "BUY", 0.75, "Williams %R supports positive momentum.")
        elif -80 < willr < -20 and willr < -50:
            add("Williams %R", "SELL", 0.75, "Williams %R supports negative momentum.")
        else:
            add("Williams %R", None, 0.75, "Williams %R is at an extreme; wait for confirmation.")

    # 11. Rate-of-change momentum
    roc = _number(snapshot, "roc_10")
    if roc is not None:
        if roc > 0:
            add("Price ROC", "BUY", 0.75, f"10-period rate of change is positive at {roc:.2f}%.")
        elif roc < 0:
            add("Price ROC", "SELL", 0.75, f"10-period rate of change is negative at {roc:.2f}%.")
        else:
            add("Price ROC", None, 0.75, "Price ROC is neutral.")

    # 12. Structure / breakout confirmation
    swing_high = _number(snapshot, "swing_high")
    swing_low = _number(snapshot, "swing_low")
    if swing_high is not None and swing_low is not None:
        if price > swing_high:
            add("Structure breakout", "BUY", 1.5, "Price has broken above the latest confirmed swing high.")
        elif price < swing_low:
            add("Structure breakdown", "SELL", 1.5, "Price has broken below the latest confirmed swing low.")
        else:
            add("Market structure", None, 1.5, "Price remains inside the latest confirmed swing range.")

    total = scores["BUY"] + scores["SELL"]
    if total <= 0:
        signal = "HOLD"
        alignment = 0
    else:
        strongest = max(scores, key=scores.get)
        weakest = min(scores, key=scores.get)
        edge = scores[strongest] - scores[weakest]
        alignment = round(scores[strongest] / total * 100)
        # Require meaningful confluence; do not turn a tiny edge into a trade.
        signal = strongest if scores[strongest] >= 6 and edge >= 2 else "HOLD"

    trend = "Bullish" if scores["BUY"] > scores["SELL"] else "Bearish" if scores["SELL"] > scores["BUY"] else "Neutral"

    return {
        "signal": signal,
        "trend": trend,
        "bullish_score": round(scores["BUY"], 2),
        "bearish_score": round(scores["SELL"], 2),
        "technical_alignment": alignment,
        "strategies": strategies,
        "strategy_count": len(strategies),
    }
