# from src.analysis.trade_plan_engine import TradePlanEngine
# from src.data.historical_candle_loader import load_historical_candles


# def main():

#     print()
#     print("=" * 60)
#     print("      MARKET STRUCTURE TRADE PLAN TEST")
#     print("=" * 60)

#     # ---------------------------------------------------------
#     # 1. Load historical candles
#     # ---------------------------------------------------------

#     print()
#     print("Loading historical candles...")

#     candles = load_historical_candles(
#         symbol="TCS.NS",
#         interval="1m",
#         max_candles=200,
#     )

#     print(f"Historical candles : {candles.count()}")

#     # ---------------------------------------------------------
#     # 2. Convert candles to DataFrame
#     # ---------------------------------------------------------

#     data = candles.get_dataframe()

#     print(f"DataFrame candles  : {len(data)}")

#     # ---------------------------------------------------------
#     # 3. Create analysis inputs
#     # ---------------------------------------------------------

#     latest = candles.get_latest()

#     snapshot = {
#         "symbol": latest["symbol"],
#         "price": float(latest["close"]),
#         "atr_14": 8.40,
#     }

#     technical = {
#         "signal": "BUY",
#     }

#     decision = {
#         "final_signal": "BUY",
#     }

#     # ---------------------------------------------------------
#     # 4. Generate trade plan
#     # ---------------------------------------------------------

#     engine = TradePlanEngine()

#     plan = engine.create_plan(
#         snapshot=snapshot,
#         technical_signal=technical,
#         decision=decision,
#         data=data,
#     )

#     # ---------------------------------------------------------
#     # 5. Display result
#     # ---------------------------------------------------------

#     print()
#     print("===== TRADE PLAN =====")

#     print(f"Symbol          : {plan['symbol']}")
#     print(f"Signal          : {plan['signal']}")
#     print(f"Entry           : ₹{plan['entry']}")

#     print(f"ATR             : ₹{plan['atr']}")

#     print(f"Swing High      : ₹{plan['swing_high']}")
#     print(f"Swing Low       : ₹{plan['swing_low']}")
#     print(f"ATR Buffer      : ₹{plan['atr_buffer']}")

#     print(f"Stop Loss       : ₹{plan['stop_loss']}")
#     print(f"Target 1        : ₹{plan['target_1']}")
#     print(f"Target 2        : ₹{plan['target_2']}")

#     print(f"Risk / Share    : ₹{plan['risk_per_share']}")

#     print(
#         f"Risk / Reward   : "
#         f"1:{plan['risk_reward_1']} / "
#         f"1:{plan['risk_reward_2']}"
#     )

#     print(f"Position Size   : {plan['position_size']}")
#     print(f"Trailing Stop   : ₹{plan['trailing_stop']}")

#     print(f"Structure Valid : {plan['structure_valid']}")

#     print()
#     print(f"Account Size    : ₹{plan['account_size']:.2f}")
#     print(f"Risk            : {plan['risk_percent']}%")

#     print()
#     print(f"Reason          : {plan['reason']}")

#     print()
#     print("=" * 60)
#     print("   MARKET STRUCTURE TRADE PLAN COMPLETE")
#     print("=" * 60)


# if __name__ == "__main__":
#     main()