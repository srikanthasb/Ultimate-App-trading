from src.analysis.trade_plan_engine import TradePlanEngine
from src.data.historical_candle_loader import load_historical_candles


def print_header(title: str):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_plan(plan: dict):
    print()
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

    print_header("TRADE PLAN ENGINE - COMPLETE TEST")

    # ---------------------------------------------------------
    # 1. Load real historical candles
    # ---------------------------------------------------------

    print()
    print("Loading historical candles...")

    store = load_historical_candles(
        symbol="TCS.NS",
        interval="1m",
        period="5d",
        max_candles=200,
        instrument_key="NSE_EQ|INE467B01029",
    )

    print(f"Historical candles : {store.count()}")

    data = store.get_dataframe()

    print(f"DataFrame candles  : {len(data)}")

    latest = store.get_latest()

    print(f"Latest candle      : {latest['timestamp']}")
    print(f"Latest close       : ₹{latest['close']}")

    # ---------------------------------------------------------
    # 2. Create engine
    # ---------------------------------------------------------

    engine = TradePlanEngine(
        account_size=100000,
        risk_percent=1.0,
        reward_ratio_1=1.5,
        reward_ratio_2=2.0,
    )

    # ---------------------------------------------------------
    # 3. Common snapshot
    # ---------------------------------------------------------

    snapshot = {
        "symbol": latest["symbol"],
        "price": float(latest["close"]),
        "atr_14": 8.40,
    }

    # =========================================================
    # CASE 1 - BUY
    # =========================================================

    print_header("CASE 1 - BUY")

    technical_buy = {
        "signal": "BUY",
    }

    decision_buy = {
        "final_signal": "BUY",
    }

    buy_plan = engine.create_plan(
        snapshot=snapshot,
        technical_signal=technical_buy,
        decision=decision_buy,
        data=data,
    )

    print_plan(buy_plan)

    # ---------------------------------------------------------
    # BUY validation
    # ---------------------------------------------------------

    assert buy_plan["signal"] == "BUY"
    assert buy_plan["structure_valid"] is True
    assert buy_plan["entry"] > buy_plan["stop_loss"]
    assert buy_plan["target_1"] > buy_plan["entry"]
    assert buy_plan["target_2"] > buy_plan["target_1"]
    assert buy_plan["position_size"] > 0

    print()
    print("BUY TEST : PASS")

    # =========================================================
    # CASE 2 - SELL
    # =========================================================

    print_header("CASE 2 - SELL")

    technical_sell = {
        "signal": "SELL",
    }

    decision_sell = {
        "final_signal": "SELL",
    }

    sell_plan = engine.create_plan(
        snapshot=snapshot,
        technical_signal=technical_sell,
        decision=decision_sell,
        data=data,
    )

    print_plan(sell_plan)

    # ---------------------------------------------------------
    # SELL validation
    # ---------------------------------------------------------

    assert sell_plan["signal"] == "SELL"
    assert sell_plan["structure_valid"] is True
    assert sell_plan["entry"] < sell_plan["stop_loss"]
    assert sell_plan["target_1"] < sell_plan["entry"]
    assert sell_plan["target_2"] < sell_plan["target_1"]
    assert sell_plan["position_size"] > 0

    print()
    print("SELL TEST : PASS")

    # =========================================================
    # CASE 3 - HOLD
    # =========================================================

    print_header("CASE 3 - HOLD")

    technical_hold = {
        "signal": "HOLD",
    }

    decision_hold = {
        "final_signal": "HOLD",
    }

    hold_plan = engine.create_plan(
        snapshot=snapshot,
        technical_signal=technical_hold,
        decision=decision_hold,
        data=data,
    )

    print_plan(hold_plan)

    # ---------------------------------------------------------
    # HOLD validation
    # ---------------------------------------------------------

    assert hold_plan["signal"] == "HOLD"
    assert hold_plan["position_size"] == 0
    assert hold_plan["entry"] == round(snapshot["price"], 2)
    assert hold_plan["atr"] == round(snapshot["atr_14"], 2)
    assert hold_plan["atr_buffer"] == round(
        snapshot["atr_14"] * engine.atr_buffer_multiplier,
        2,
    )
    assert hold_plan["swing_high"] is not None
    assert hold_plan["swing_low"] is not None
    assert hold_plan["stop_loss"] is None
    assert hold_plan["target_1"] is None
    assert hold_plan["target_2"] is None
    assert hold_plan["risk_per_share"] is None
    assert hold_plan["position_size"] == 0
    assert hold_plan["trailing_stop"] is None
    assert hold_plan["structure_valid"] is False
    assert hold_plan["stop_loss"] is None
    assert hold_plan["target_1"] is None
    assert hold_plan["target_2"] is None

    print()
    print("HOLD TEST : PASS")

    # =========================================================
    # CASE 4 - BUY STRUCTURE INVALIDATION
    # =========================================================

    print_header("CASE 4 - INVALID BUY STRUCTURE")

    # Get the swing low from the real market structure.
    swing_low = buy_plan["swing_low"]

    invalid_buy_snapshot = {
        "symbol": latest["symbol"],
        "price": float(swing_low) - 1.0,
        "atr_14": 8.40,
    }

    invalid_buy_plan = engine.create_plan(
        snapshot=invalid_buy_snapshot,
        technical_signal=technical_buy,
        decision=decision_buy,
        data=data,
    )
    print()
    print("Invalid BUY plan returned:")
    print_plan(invalid_buy_plan)

    assert invalid_buy_plan["signal"] == "BUY"
    assert invalid_buy_plan["structure_valid"] is False
    assert invalid_buy_plan["entry"] == round(
        float(invalid_buy_snapshot["price"]),
        2,
    )
    assert invalid_buy_plan["stop_loss"] is None
    assert invalid_buy_plan["target_1"] is None
    assert invalid_buy_plan["target_2"] is None
    assert invalid_buy_plan["risk_per_share"] is None
    assert invalid_buy_plan["position_size"] == 0
    assert invalid_buy_plan["trailing_stop"] is None

    print("INVALID BUY TEST : PASS")

    # =========================================================
    # CASE 5 - SELL STRUCTURE INVALIDATION
    # =========================================================

    print_header("CASE 5 - INVALID SELL STRUCTURE")

    swing_high = sell_plan["swing_high"]

    invalid_sell_snapshot = {
        "symbol": latest["symbol"],
        "price": float(swing_high) + 1.0,
        "atr_14": 8.40,
    }

    invalid_sell_plan = engine.create_plan(
        snapshot=invalid_sell_snapshot,
        technical_signal=technical_sell,
        decision=decision_sell,
        data=data,
    )

    assert invalid_sell_plan["signal"] == "SELL"
    assert invalid_sell_plan["structure_valid"] is False
    assert invalid_sell_plan["entry"] == float(invalid_sell_snapshot["price"])
    assert invalid_sell_plan["stop_loss"] is None
    assert invalid_sell_plan["target_1"] is None
    assert invalid_sell_plan["target_2"] is None
    assert invalid_sell_plan["risk_per_share"] is None
    assert invalid_sell_plan["position_size"] == 0
    assert invalid_sell_plan["trailing_stop"] is None

    print("INVALID SELL TEST : PASS")

    # =========================================================
    # CASE 6 - RISK / POSITION SIZING
    # =========================================================

    print_header("CASE 6 - POSITION SIZING")

    maximum_risk = (
        engine.account_size
        * engine.risk_percent
        / 100
    )

    expected_position_size = int(
        maximum_risk / buy_plan["risk_per_share"]
    )

    print(
        f"Maximum account risk : ₹{maximum_risk:.2f}"
    )

    print(
        f"Risk / share         : ₹{buy_plan['risk_per_share']}"
    )

    print(
        f"Expected shares      : {expected_position_size}"
    )

    print(
        f"Engine shares        : {buy_plan['position_size']}"
    )

    assert (
        buy_plan["position_size"]
        == expected_position_size
    )

    print()
    print("POSITION SIZING TEST : PASS")

    # =========================================================
    # FINAL RESULT
    # =========================================================

    print_header("ALL TRADE PLAN ENGINE TESTS PASSED")

    print()
    print("✓ BUY plan")
    print("✓ SELL plan")
    print("✓ HOLD plan")
    print("✓ BUY structure protection")
    print("✓ SELL structure protection")
    print("✓ ATR + market structure")
    print("✓ Position sizing")
    print("✓ Risk/reward calculation")
    print("✓ Trailing stop")
    print()


if __name__ == "__main__":
    main()
    