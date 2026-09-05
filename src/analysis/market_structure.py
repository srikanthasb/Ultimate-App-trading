import pandas as pd


def find_recent_swing(
    data: pd.DataFrame,
    lookback: int = 2,
) -> dict:
    """
    Find the most recent confirmed swing high and swing low.

    A swing low is a candle whose Low is lower than the
    surrounding candles within the specified lookback.

    A swing high is a candle whose High is higher than the
    surrounding candles within the specified lookback.

    The current candle is not used as a confirmed swing.
    """

    if data is None or data.empty:
        raise ValueError("Market data is empty.")

    required_columns = ["High", "Low"]

    for column in required_columns:
        if column not in data.columns:
            raise ValueError(
                f"Market data is missing required column: {column}"
            )

    if lookback <= 0:
        raise ValueError("lookback must be greater than 0.")

    if len(data) < (lookback * 2 + 1):
        raise ValueError(
            "Not enough candles to identify swing points."
        )

    swing_high = None
    swing_low = None

    # Exclude the latest candle because it cannot yet be
    # confirmed as a swing.
    last_confirmable_index = len(data) - lookback - 1

    for i in range(
        lookback,
        last_confirmable_index + 1,
    ):
        current_high = data["High"].iloc[i]
        current_low = data["Low"].iloc[i]

        left_highs = data["High"].iloc[
            i - lookback:i
        ]

        right_highs = data["High"].iloc[
            i + 1:i + lookback + 1
        ]

        left_lows = data["Low"].iloc[
            i - lookback:i
        ]

        right_lows = data["Low"].iloc[
            i + 1:i + lookback + 1
        ]

        is_swing_high = (
            current_high > left_highs.max()
            and current_high > right_highs.max()
        )

        is_swing_low = (
            current_low < left_lows.min()
            and current_low < right_lows.min()
        )

        timestamp = data.index[i]

        if is_swing_high:
            swing_high = {
                "timestamp": timestamp,
                "price": float(current_high),
            }

        if is_swing_low:
            swing_low = {
                "timestamp": timestamp,
                "price": float(current_low),
            }

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
    }