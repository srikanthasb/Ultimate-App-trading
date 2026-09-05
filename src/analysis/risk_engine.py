def calculate_risk(
    technical_signal: dict,
    ai_analysis: dict,
    decision: dict,
) -> dict:
    """
    Evaluate the uncertainty surrounding the final market decision.

    The Risk Engine does NOT change the final BUY/SELL/HOLD decision.
    It only evaluates the strength and consistency of the evidence.

    No AI or LLM is involved.
    """

    if not technical_signal:
        raise ValueError("Technical signal is empty.")

    if not ai_analysis:
        raise ValueError("AI analysis is empty.")

    if not decision:
        raise ValueError("Decision is empty.")

    technical_alignment = technical_signal["technical_alignment"]
    ai_confidence = ai_analysis["confidence"]
    agreement = decision["agreement"]

    risk_score = 0
    reasons = []

    # ---------------------------------------------------------
    # 1. Technical alignment
    # ---------------------------------------------------------

    if technical_alignment >= 80:
        reasons.append(
            "Technical indicators show strong alignment."
        )

    elif technical_alignment >= 65:
        risk_score += 1
        reasons.append(
            "Technical indicators show moderate alignment."
        )

    else:
        risk_score += 2
        reasons.append(
            "Technical indicators show weak alignment."
        )

    # ---------------------------------------------------------
    # 2. AI confidence
    # ---------------------------------------------------------

    if ai_confidence >= 80:
        reasons.append(
            "AI analysis reports high confidence."
        )

    elif ai_confidence >= 60:
        risk_score += 1
        reasons.append(
            "AI analysis reports moderate confidence."
        )

    else:
        risk_score += 2
        reasons.append(
            "AI analysis reports low confidence."
        )

    # ---------------------------------------------------------
    # 3. Agreement between systems
    # ---------------------------------------------------------

    if agreement:
        reasons.append(
            "Technical analysis and AI analysis agree."
        )

    else:
        risk_score += 2
        reasons.append(
            "Technical analysis and AI analysis disagree."
        )

    # ---------------------------------------------------------
    # 4. Final risk classification
    # ---------------------------------------------------------

    if risk_score <= 0:
        risk = "Low"

    elif risk_score <= 2:
        risk = "Moderate"

    else:
        risk = "High"

    return {
        "risk": risk,
        "risk_score": risk_score,
        "reasons": reasons,
    }