from src.ai.llm import llm
from langchain_core.prompts import ChatPromptTemplate
import json


class AIAnalyst:
    """
    AI-powered interpretation of a technical market snapshot.

    The AI does NOT calculate indicators.
    It only interprets the values calculated by indicators.py.
    """

    def __init__(self):
        self.llm = llm

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
You are a professional technical market analyst.

Analyze the supplied market snapshot and the deterministic strategy-confluence result when present.

IMPORTANT:
- Do not calculate technical indicators yourself.
- Use only the values provided.
- Do not invent missing data.
- Explain the reasoning behind your conclusion.
- Do not promise profit or certainty.
- A BUY/SELL conclusion must be treated as conditional guidance, not a guarantee.

Return ONLY valid JSON using this structure:

{{
    "symbol": "...",
    "trend": "Bullish | Bearish | Neutral",
    "momentum": "Strong Positive | Positive | Neutral | Negative | Strong Negative",
    "signal": "BUY | SELL | HOLD",
    "confidence": 0,
    "summary": "...",
    "reasons": [
        "...",
        "...",
        "..."
    ]
}}
"""
            ),
            (
                "human",
                """
Analyze this market snapshot:

{snapshot}
"""
            ),
        ])

    def analyze(self, snapshot: dict) -> dict:
        """
        Send a market snapshot to the LLM and return structured analysis.
        """

        if not snapshot:
            raise ValueError("Market snapshot is empty.")

        messages = self.prompt.format_messages(
            snapshot=json.dumps(snapshot, indent=2)
        )

        response = self.llm.invoke(messages)

        content = response.content.strip()

        if content.startswith("```"):
            content = (
                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        try:
            analysis = json.loads(content)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"AI returned invalid JSON:\n{content}"
            ) from exc

        # ------------------------------------------
        # Normalize confidence to 0–100
        # ------------------------------------------

        confidence = analysis.get("confidence", 0)

        if isinstance(confidence, float) and confidence <= 1:
            confidence *= 100

        analysis["confidence"] = int(round(confidence))

        return analysis