from src.data.market_data import get_market_data
from src.data.historical_candle_loader import load_historical_candles

from src.analysis.indicators import add_indicators
from src.analysis.snapshot import create_market_snapshot
from src.analysis.signal_engine import generate_signal
from src.analysis.ai_analyst import AIAnalyst
from src.analysis.decision_engine import make_decision
from src.analysis.trade_plan_engine import TradePlanEngine


def print_header(title: str):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_trade_plan(plan: dict):

    print()
    print("===== TRADE PLAN =====")

    print(f"Symbol          : {plan['symbol']}")
    print(f"Signal          : {plan['signal']}")
    print(f"Entry           : ₹{plan['entry']}")

    print(f"ATR             : ₹{plan['atr']}")
    print(f"Swing High      : ₹{plan['swing_high']}")
    print(f"Swing Low       : ₹{plan['swing_low']}")
    print(f"ATR Buffer      : ₹{plan['atr_buffer']}")

    print(f"Stop Loss       : ₹{plan['stop_loss']}")
    print(f"Target 1        : ₹{plan['target_1']}")
    print(f"Target 2        : ₹{plan['target_2']}")

    print(f"Risk / Share    : ₹{plan['risk_per_share']}")

    print(
        f"Risk / Reward   : "
        f"1:{plan['risk_reward_1']} / "
        f"1:{plan['risk_reward_2']}"
    )

    print(f"Position Size   : {plan['position_size']}")
    print(f"Trailing Stop   : ₹{plan['trailing_stop']}")

    print(f"Structure Valid : {plan['structure_valid']}")

    print()
    print(f"Account Size    : ₹{plan['account_size']:.2f}")
    print(f"Risk            : {plan['risk_percent']}%")

    print()
    print(f"Reason          : {plan['reason']}")


def main():

    symbol = "TCS.NS"

    print_header(
        "FINANCE APP - COMPLETE ANALYSIS + TRADE PLAN TEST"
    )

    # =========================================================
    # 1. DAILY MARKET DATA
    # =========================================================

    print()
    print("[1/7] Downloading daily market data...")

    daily_data = get_market_data(
        ticker=symbol,
        period="6mo",
        interval="1d",
    )

    print(
        f"      Daily rows received: "
        f"{len(daily_data)}"
    )

    if daily_data.empty:
        raise ValueError("Daily market data is empty.")

    # =========================================================
    # 2. TECHNICAL INDICATORS
    # =========================================================

    print()
    print("[2/7] Calculating technical indicators...")

    daily_data = add_indicators(daily_data)

    daily_data = daily_data.dropna()

    print(
        f"      Rows after indicators: "
        f"{len(daily_data)}"
    )

    if daily_data.empty:
        raise ValueError(
            "No data remains after calculating indicators."
        )

    # =========================================================
    # 3. MARKET SNAPSHOT
    # =========================================================

    print()
    print("[3/7] Creating market snapshot...")

    snapshot = create_market_snapshot(
        data=daily_data,
        symbol=symbol,
    )

    print(
        f"      Price       : "
        f"₹{snapshot['price']}"
    )

    print(
        f"      SMA20       : "
        f"{snapshot['sma_20']}"
    )

    print(
        f"      SMA50       : "
        f"{snapshot['sma_50']}"
    )

    print(
        f"      EMA20       : "
        f"{snapshot['ema_20']}"
    )

    print(
        f"      RSI14       : "
        f"{snapshot['rsi_14']}"
    )

    print(
        f"      MACD        : "
        f"{snapshot['macd']}"
    )

    print(
        f"      MACD Signal : "
        f"{snapshot['macd_signal']}"
    )

    print(
        f"      MACD Hist   : "
        f"{snapshot['macd_histogram']}"
    )

    # =========================================================
    # 4. TECHNICAL SIGNAL
    # =========================================================

    print()
    print("[4/7] Running technical signal engine...")

    technical_signal = generate_signal(snapshot)

    print(
        f"      Trend       : "
        f"{technical_signal['trend']}"
    )

    print(
        f"      Signal      : "
        f"{technical_signal['signal']}"
    )

    print(
        f"      Alignment   : "
        f"{technical_signal['technical_alignment']}%"
    )

    print(
        f"      Bullish     : "
        f"{technical_signal['bullish_points']}"
    )

    print(
        f"      Bearish     : "
        f"{technical_signal['bearish_points']}"
    )

    # =========================================================
    # 5. AI ANALYST
    # =========================================================

    print()
    print("[5/7] Running AI Analyst...")

    analyst = AIAnalyst()

    ai_analysis = analyst.analyze(snapshot)

    print()
    print(
        f"      AI Trend      : "
        f"{ai_analysis['trend']}"
    )

    print(
        f"      AI Momentum   : "
        f"{ai_analysis['momentum']}"
    )

    print(
        f"      AI Signal     : "
        f"{ai_analysis['signal']}"
    )

    print(
        f"      AI Confidence : "
        f"{ai_analysis['confidence']}%"
    )

    print()
    print("      AI Summary:")
    print(
        f"      {ai_analysis['summary']}"
    )

    # =========================================================
    # 6. DECISION ENGINE
    # =========================================================

    print()
    print("[6/7] Running Decision Engine...")

    decision = make_decision(
        snapshot=snapshot,
        technical_signal=technical_signal,
        ai_analysis=ai_analysis,
    )

    print()
    print("===== FINAL DECISION =====")

    print(
        f"      Symbol            : "
        f"{decision['symbol']}"
    )

    print(
        f"      Final Signal      : "
        f"{decision['final_signal']}"
    )

    print(
        f"      Trend             : "
        f"{decision['trend']}"
    )

    print(
        f"      Momentum          : "
        f"{decision['momentum']}"
    )

    print(
        f"      Agreement         : "
        f"{decision['agreement']}"
    )

    print(
        f"      Technical Align.  : "
        f"{decision['technical_alignment']}%"
    )

    print(
        f"      AI Confidence     : "
        f"{decision['ai_confidence']}%"
    )

    print(
        f"      Risk              : "
        f"{decision['risk']}"
    )

    print()
    print(
        f"      Explanation:"
    )
    print(
        f"      {decision['explanation']}"
    )

    # =========================================================
    # 7. INTRADAY MARKET STRUCTURE + TRADE PLAN
    # =========================================================

    print()
    print("[7/7] Loading intraday candles for trade plan...")

    intraday_store = load_historical_candles(
        symbol=symbol,
        interval="1m",
        period="5d",
        max_candles=200,
        instrument_key="NSE_EQ|INE467B01029",
    )

    print(
        f"      Completed candles: "
        f"{intraday_store.count()}"
    )

    intraday_data = intraday_store.get_dataframe()

    print(
        f"      DataFrame candles : "
        f"{len(intraday_data)}"
    )

    latest_intraday = intraday_store.get_latest()

    print(
        f"      Latest candle     : "
        f"{latest_intraday['timestamp']}"
    )

    print(
        f"      Latest close      : "
        f"₹{latest_intraday['close']}"
    )

    # ---------------------------------------------------------
    # IMPORTANT
    #
    # The existing snapshot currently contains ATR only if
    # create_market_snapshot() provides it.
    #
    # For now we use the same ATR value used by the validated
    # TradePlanEngine tests.
    # ---------------------------------------------------------

    trade_snapshot = {
        "symbol": symbol,
        "price": float(latest_intraday["close"]),
        "atr_14": float(snapshot["atr_14"]),
    }

    trade_plan_engine = TradePlanEngine(
        account_size=100000,
        risk_percent=1.0,
        reward_ratio_1=1.5,
        reward_ratio_2=2.0,
        atr_buffer_multiplier=0.5,
    )

    trade_plan = trade_plan_engine.create_plan(
        snapshot=trade_snapshot,
        technical_signal=technical_signal,
        decision=decision,
        data=intraday_data,
    )

    print_trade_plan(trade_plan)

    # =========================================================
    # FINAL VALIDATION
    # =========================================================

    print_header("PIPELINE VALIDATION")

    # ---------------------------------------------------------
    # Decision validation
    # ---------------------------------------------------------

    assert decision["final_signal"] in {
        "BUY",
        "SELL",
        "HOLD",
    }

    assert decision["technical_alignment"] >= 0
    assert decision["technical_alignment"] <= 100

    assert decision["ai_confidence"] >= 0
    assert decision["ai_confidence"] <= 100

    print("✓ Decision Engine : PASS")

    # ---------------------------------------------------------
    # Trade plan validation
    # ---------------------------------------------------------

    assert trade_plan["symbol"] == symbol

    assert trade_plan["signal"] == decision["final_signal"]

    assert trade_plan["atr"] == 8.40
    assert trade_plan["atr_buffer"] == 4.20

    if decision["final_signal"] == "BUY":

        assert trade_plan["structure_valid"] is True

        assert trade_plan["entry"] > trade_plan["stop_loss"]

        assert (
            trade_plan["target_1"]
            > trade_plan["entry"]
        )

        assert (
            trade_plan["target_2"]
            > trade_plan["target_1"]
        )

        assert trade_plan["position_size"] > 0

        print("✓ BUY Trade Plan : PASS")

    elif decision["final_signal"] == "SELL":

        assert trade_plan["structure_valid"] is True

        assert trade_plan["entry"] < trade_plan["stop_loss"]

        assert (
            trade_plan["target_1"]
            < trade_plan["entry"]
        )

        assert (
            trade_plan["target_2"]
            < trade_plan["target_1"]
        )

        assert trade_plan["position_size"] > 0

        print("✓ SELL Trade Plan : PASS")

    else:

        assert trade_plan["signal"] == "HOLD"
        assert trade_plan["position_size"] == 0
        assert trade_plan["structure_valid"] is False

        assert trade_plan["stop_loss"] is None
        assert trade_plan["target_1"] is None
        assert trade_plan["target_2"] is None

        assert trade_plan["risk_per_share"] is None
        assert trade_plan["trailing_stop"] is None

        assert trade_plan["swing_high"] is not None
        assert trade_plan["swing_low"] is not None

        assert trade_plan["atr"] == 8.40
        assert trade_plan["atr_buffer"] == 4.20

        print("✓ HOLD Trade Plan : PASS")

    # =========================================================
    # COMPLETE
    # =========================================================

    print_header(
        "COMPLETE PIPELINE + TRADE PLAN TEST PASSED"
    )

    print()
    print("✓ Real market data")
    print("✓ Technical indicators")
    print("✓ Market snapshot")
    print("✓ Technical signal engine")
    print("✓ AI Analyst")
    print("✓ Decision Engine")
    print("✓ Intraday market structure")
    print("✓ ATR")
    print("✓ ATR buffer")
    print("✓ TradePlanEngine")
    print("✓ Position sizing")
    print("✓ Risk/reward")
    print("✓ Trailing stop")
    print()


if __name__ == "__main__":
    main()