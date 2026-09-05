def make_decision(
    snapshot: dict,
    technical_signal: dict,
    ai_analysis: dict,
) -> dict:
    """
    Combine deterministic technical analysis and AI interpretation.

    The Decision Engine does not calculate indicators and does not
    ask the AI to make a new prediction. It evaluates the agreement
    between independently produced analyses.
    """

    if not snapshot:
        raise ValueError("Market snapshot is empty.")

    if not technical_signal:
        raise ValueError("Technical signal is empty.")

    if not ai_analysis:
        raise ValueError("AI analysis is empty.")

    technical = technical_signal["signal"]
    ai_signal = ai_analysis["signal"]

    technical_alignment = technical_signal["technical_alignment"]
    ai_confidence = ai_analysis["confidence"]

    # Determine agreement
    agreement = technical == ai_signal

    # Determine final signal
    if agreement:
        final_signal = technical
    else:
        final_signal = "HOLD"

    # Determine overall trend
    if technical_signal["trend"] == ai_analysis["trend"]:
        trend = technical_signal["trend"]
    else:
        trend = "Mixed"

    # Determine momentum from AI interpretation
    momentum = ai_analysis["momentum"]

    # Basic risk classification
    if agreement and technical_alignment >= 80 and ai_confidence >= 70:
        risk = "Moderate"

    elif agreement:
        risk = "Moderate-High"

    else:
        risk = "High"

    # Human-readable explanation
    if agreement:
        explanation = (
            f"Technical analysis and AI analysis agree on {final_signal}. "
            f"Technical alignment is {technical_alignment}% and "
            f"AI confidence is {ai_confidence}%."
        )
    else:
        explanation = (
            "Technical analysis and AI analysis disagree. "
            "The Decision Engine therefore recommends HOLD until "
            "the conflicting signals are resolved."
        )

    return {
        "symbol": snapshot["symbol"],
        "final_signal": final_signal,
        "trend": trend,
        "momentum": momentum,
        "agreement": agreement,
        "technical_alignment": technical_alignment,
        "ai_confidence": ai_confidence,
        "risk": risk,
        "explanation": explanation,
    }