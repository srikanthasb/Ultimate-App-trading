import pandas as pd

from src.analysis.ai_analyst import AIAnalyst
from src.analysis.decision_engine import make_decision
from src.analysis.indicators import add_indicators
from src.analysis.market_structure import find_recent_swing
from src.analysis.risk_engine import calculate_risk
from src.analysis.signal_engine import generate_signal
from src.analysis.snapshot import create_market_snapshot
from src.analysis.trade_plan_engine import TradePlanEngine


class LiveAnalysisService:
    """Run the complete live guidance pipeline on one instrument/timeframe."""

    def __init__(self):
        self.ai_analyst = AIAnalyst()
        self.trade_plan_engine = TradePlanEngine(
            account_size=100000,
            risk_percent=1.0,
            reward_ratio_1=1.5,
            reward_ratio_2=2.0,
            atr_buffer_multiplier=0.5,
        )

    def analyze(self, candles: list[dict], current_price: float | None = None) -> dict:
        if not candles:
            raise ValueError("No live candles available.")

        data = pd.DataFrame(candles)
        required = {"symbol", "interval", "timestamp", "open", "high", "low", "close", "volume"}
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f"Live candles are missing fields: {sorted(missing)}")

        symbols = {str(v).upper() for v in data["symbol"].dropna().unique()}
        intervals = {str(v).lower() for v in data["interval"].dropna().unique()}
        instrument_keys = {str(v) for v in data.get("instrument_key", pd.Series(dtype=str)).dropna().unique()}
        if len(symbols) != 1:
            raise ValueError(f"Mixed instruments detected in live candles: {sorted(symbols)}")
        if len(intervals) != 1:
            raise ValueError(f"Mixed timeframes detected in live candles: {sorted(intervals)}")
        if len(instrument_keys) > 1:
            raise ValueError(f"Mixed instrument keys detected in live candles: {sorted(instrument_keys)}")

        data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
        data = data.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
        if data.empty:
            raise ValueError("Live candle timestamps are invalid.")

        data = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })

        symbol = next(iter(symbols))
        interval = next(iter(intervals))

        data = add_indicators(data)
        data = data.dropna()
        if data.empty:
            raise ValueError("Not enough live candles to calculate indicators.")

        snapshot = create_market_snapshot(data=data, symbol=symbol)

        # Structure is calculated from the same verified candle series.
        structure = find_recent_swing(data=data, lookback=2)
        swing_high = structure.get("swing_high")
        swing_low = structure.get("swing_low")
        snapshot["interval"] = interval
        snapshot["swing_high"] = float(swing_high["price"]) if swing_high else None
        snapshot["swing_low"] = float(swing_low["price"]) if swing_low else None
        # Indicators are based on completed candles; trade entry is based on the live LTP.
        if current_price is not None:
            snapshot["price"] = float(current_price)

        technical_signal = generate_signal(snapshot)
        ai_analysis = self.ai_analyst.analyze(snapshot)
        decision = make_decision(
            snapshot=snapshot,
            technical_signal=technical_signal,
            ai_analysis=ai_analysis,
        )
        risk = calculate_risk(
            technical_signal=technical_signal,
            ai_analysis=ai_analysis,
            decision=decision,
        )
        trade_plan = self.trade_plan_engine.create_plan(
            snapshot=snapshot,
            technical_signal=technical_signal,
            decision=decision,
            data=data,
        )

        return {
            "snapshot": snapshot,
            "technical_signal": technical_signal,
            "ai_analysis": ai_analysis,
            "decision": decision,
            "risk": risk,
            "trade_plan": trade_plan,
        }
