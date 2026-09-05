from src.analysis.market_structure import find_recent_swing


class TradePlanEngine:
    """Create a structure- and ATR-aware plan without placing orders."""

    def __init__(
        self,
        account_size: float = 100000,
        risk_percent: float = 1.0,
        reward_ratio_1: float = 1.5,
        reward_ratio_2: float = 2.0,
        atr_buffer_multiplier: float = 0.5,
    ):
        if account_size <= 0:
            raise ValueError("account_size must be greater than 0.")
        if risk_percent <= 0:
            raise ValueError("risk_percent must be greater than 0.")
        if reward_ratio_1 <= 0 or reward_ratio_2 <= 0:
            raise ValueError("Reward ratios must be greater than 0.")
        if reward_ratio_2 <= reward_ratio_1:
            raise ValueError("reward_ratio_2 must be greater than reward_ratio_1.")
        if atr_buffer_multiplier < 0:
            raise ValueError("atr_buffer_multiplier cannot be negative.")

        self.account_size = account_size
        self.risk_percent = risk_percent
        self.reward_ratio_1 = reward_ratio_1
        self.reward_ratio_2 = reward_ratio_2
        self.atr_buffer_multiplier = atr_buffer_multiplier

    @staticmethod
    def _price(level):
        return round(float(level), 2) if level is not None else None

    def create_plan(self, snapshot: dict, technical_signal: dict, decision: dict, data) -> dict:
        if not snapshot:
            raise ValueError("Snapshot is empty.")
        if not technical_signal:
            raise ValueError("Technical signal is empty.")
        if not decision:
            raise ValueError("Decision is empty.")
        if data is None or data.empty:
            raise ValueError("Market data is empty.")

        price = float(snapshot["price"])
        atr = float(snapshot["atr_14"])
        signal = decision["final_signal"]

        structure = find_recent_swing(data=data, lookback=2)
        swing_high = structure.get("swing_high")
        swing_low = structure.get("swing_low")
        swing_high_price = float(swing_high["price"]) if swing_high else None
        swing_low_price = float(swing_low["price"]) if swing_low else None
        atr_buffer = atr * self.atr_buffer_multiplier

        base = {
            "symbol": snapshot["symbol"],
            "signal": signal,
            "entry": self._price(price),
            "stop_loss": None,
            "target_1": None,
            "target_2": None,
            "risk_per_share": None,
            "risk_reward_1": self.reward_ratio_1,
            "risk_reward_2": self.reward_ratio_2,
            "position_size": 0,
            "trailing_stop": None,
            "swing_high": self._price(swing_high_price),
            "swing_low": self._price(swing_low_price),
            "support": self._price(swing_low_price),
            "resistance": self._price(swing_high_price),
            "atr": round(atr, 2),
            "atr_buffer": round(atr_buffer, 2),
            "structure_valid": False,
            "account_size": self.account_size,
            "risk_percent": self.risk_percent,
        }

        if signal == "HOLD":
            base["reason"] = (
                "HOLD: no executable position is recommended. "
                "The chart still shows the latest confirmed support/resistance "
                "so the trader can wait for a clean breakout or rejection."
            )
            base["monitor_long_above"] = self._price(swing_high_price) if swing_high_price and price < swing_high_price else None
            base["monitor_short_below"] = self._price(swing_low_price) if swing_low_price and price > swing_low_price else None
            return base

        if signal == "BUY":
            if swing_low_price is None:
                return self._invalid_plan(base, "No recent swing low is available.")
            if price <= swing_low_price:
                return self._invalid_plan(base, f"BUY setup rejected: price ₹{price:.2f} is at or below support ₹{swing_low_price:.2f}.")
            stop_loss = swing_low_price - atr_buffer
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                return self._invalid_plan(base, "Calculated BUY risk per share is invalid.")
            target_1 = price + risk_per_share * self.reward_ratio_1
            target_2 = price + risk_per_share * self.reward_ratio_2
            # Do not manufacture a setup whose first target is already beyond
            # the next confirmed resistance.  It is safer to wait for room.
            if swing_high_price is not None and swing_high_price > price and swing_high_price < target_1:
                return self._invalid_plan(base, "BUY setup rejected: confirmed resistance is too close for the minimum 1.5R target.")
            return self._finalize(base, price, stop_loss, target_1, target_2, risk_per_share, "BUY")

        if signal == "SELL":
            if swing_high_price is None:
                return self._invalid_plan(base, "No recent swing high is available.")
            if price >= swing_high_price:
                return self._invalid_plan(base, f"SELL setup rejected: price ₹{price:.2f} is at or above resistance ₹{swing_high_price:.2f}.")
            stop_loss = swing_high_price + atr_buffer
            risk_per_share = stop_loss - price
            if risk_per_share <= 0:
                return self._invalid_plan(base, "Calculated SELL risk per share is invalid.")
            target_1 = price - risk_per_share * self.reward_ratio_1
            target_2 = price - risk_per_share * self.reward_ratio_2
            if swing_low_price is not None and swing_low_price < price and swing_low_price > target_1:
                return self._invalid_plan(base, "SELL setup rejected: confirmed support is too close for the minimum 1.5R target.")
            return self._finalize(base, price, stop_loss, target_1, target_2, risk_per_share, "SELL")

        raise ValueError(f"Unsupported signal: {signal}")

    def _finalize(self, base, entry, stop_loss, target_1, target_2, risk_per_share, signal):
        maximum_account_risk = self.account_size * self.risk_percent / 100
        position_size = int(maximum_account_risk / risk_per_share)
        trailing_distance = risk_per_share * 0.5
        trailing_stop = entry - trailing_distance if signal == "BUY" else entry + trailing_distance
        base.update({
            "entry": self._price(entry),
            "stop_loss": self._price(stop_loss),
            "target_1": self._price(target_1),
            "target_2": self._price(target_2),
            "risk_per_share": self._price(risk_per_share),
            "position_size": max(0, position_size),
            "trailing_stop": self._price(trailing_stop),
            "structure_valid": position_size > 0,
            "reason": f"{signal} plan generated from multi-strategy confluence, ATR and confirmed market structure.",
        })
        return base

    def _invalid_plan(self, base, reason):
        base = dict(base)
        base["structure_valid"] = False
        base["reason"] = reason
        return base
