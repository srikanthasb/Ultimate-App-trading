from src.data.market_data import get_market_data
from src.analysis.indicators import add_indicators
from src.analysis.snapshot import create_market_snapshot
from src.analysis.signal_engine import generate_signal
from src.analysis.ai_analyst import AIAnalyst
from src.analysis.decision_engine import make_decision
from src.analysis.risk_engine import calculate_risk


class AnalysisService:
    """
    Orchestrates the complete market-analysis pipeline.

    The service coordinates the different layers of the application
    but does not perform indicator calculations itself.
    """

    def __init__(
        self,
        period: str = "6mo",
        interval: str = "1d",
    ):
        self.period = period
        self.interval = interval
        self.ai_analyst = AIAnalyst()

    def analyze(self, symbol: str) -> dict:
        """
        Run the complete analysis pipeline for a symbol.

        Pipeline:

            Market Data
                ↓
            Indicators
                ↓
            Snapshot
                ↓
            Technical Signal
                ↓
            AI Analysis
                ↓
            Decision Engine
        """

        if not symbol or not symbol.strip():
            raise ValueError("Symbol is required.")

        symbol = symbol.strip().upper()

        # 1. Market data
        data = get_market_data(
            ticker=symbol,
            period=self.period,
            interval=self.interval,
        )

        # 2. Technical indicators
        data = add_indicators(data)

        # Indicators such as SMA50 and MACD require
        # sufficient historical observations.
        data = data.dropna()

        if data.empty:
            raise ValueError(
                f"Not enough data to calculate indicators for {symbol}."
            )

        # 3. Market snapshot
        snapshot = create_market_snapshot(
            data=data,
            symbol=symbol,
        )

        # 4. Deterministic technical analysis
        technical_signal = generate_signal(snapshot)

        # 5. AI interpretation
        ai_analysis = self.ai_analyst.analyze(snapshot)

        # 6. Final decision
        decision = make_decision(
            snapshot=snapshot,
            technical_signal=technical_signal,
            ai_analysis=ai_analysis,
        )
        # 7. Risk assessment
        risk = calculate_risk(
            technical_signal=technical_signal,
            ai_analysis=ai_analysis,
            decision=decision,
        )

        # Return all layers, not just the final decision.
        return {
            "snapshot": snapshot,
            "technical_signal": technical_signal,
            "ai_analysis": ai_analysis,
            "decision": decision,
            "risk": risk,
        }