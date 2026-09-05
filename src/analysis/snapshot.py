import pandas as pd


def _optional_float(row, column):
    value = row.get(column)
    try:
        return float(value) if pd.notna(value) else None
    except (TypeError, ValueError):
        return None


def create_market_snapshot(data: pd.DataFrame, symbol: str) -> dict:
    if data.empty:
        raise ValueError("Market data is empty.")

    latest = data.iloc[-1]
    snapshot = {
        "symbol": symbol,
        "date": str(data.index[-1]),
        "price": float(latest["Close"]),
        "open": float(latest["Open"]),
        "high": float(latest["High"]),
        "low": float(latest["Low"]),
        "volume": int(latest["Volume"]),
        "sma_20": float(latest["SMA_20"]),
        "sma_50": float(latest["SMA_50"]),
        "ema_20": float(latest["EMA_20"]),
        "rsi_14": float(latest["RSI_14"]),
        "macd": float(latest["MACD"]),
        "macd_signal": float(latest["MACD_SIGNAL"]),
        "macd_histogram": float(latest["MACD_HIST"]),
        "atr_14": round(float(latest["ATR_14"]), 2),
    }

    optional_map = {
        "ema_50": "EMA_50", "bb_high": "BB_HIGH", "bb_low": "BB_LOW",
        "bb_mavg": "BB_MAVG", "bb_pct": "BB_PCT", "stoch_k": "STOCH_K",
        "stoch_d": "STOCH_D", "adx_14": "ADX_14", "plus_di": "PLUS_DI",
        "minus_di": "MINUS_DI", "cci_20": "CCI_20", "williams_r": "WILLIAMS_R",
        "roc_10": "ROC_10", "obv": "OBV", "obv_slope": "OBV_SLOPE",
        "vwap": "VWAP", "volume_ratio": "VOLUME_RATIO",
    }
    for key, column in optional_map.items():
        value = _optional_float(latest, column)
        if value is not None:
            snapshot[key] = round(value, 4 if key in {"bb_pct", "volume_ratio"} else 2)

    return snapshot
