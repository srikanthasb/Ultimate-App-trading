import pandas as pd

from ta.momentum import (
    RSIIndicator,
    ROCIndicator,
    StochasticOscillator,
    WilliamsRIndicator,
)
from ta.trend import (
    ADXIndicator,
    CCIIndicator,
    EMAIndicator,
    MACD,
    SMAIndicator,
)
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from ta.volatility import AverageTrueRange, BollingerBands


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Add the technical indicators used by the live guidance engine."""
    data = data.copy()
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Market data is missing columns: {sorted(missing)}")

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]

    data["SMA_20"] = SMAIndicator(close=close, window=20).sma_indicator()
    data["SMA_50"] = SMAIndicator(close=close, window=50).sma_indicator()
    data["EMA_20"] = EMAIndicator(close=close, window=20).ema_indicator()
    data["EMA_50"] = EMAIndicator(close=close, window=50).ema_indicator()
    data["RSI_14"] = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close)
    data["MACD"] = macd.macd()
    data["MACD_SIGNAL"] = macd.macd_signal()
    data["MACD_HIST"] = macd.macd_diff()

    atr = AverageTrueRange(high=high, low=low, close=close, window=14)
    data["ATR_14"] = atr.average_true_range()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    data["BB_HIGH"] = bb.bollinger_hband()
    data["BB_LOW"] = bb.bollinger_lband()
    data["BB_MAVG"] = bb.bollinger_mavg()
    data["BB_PCT"] = bb.bollinger_pband()

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    data["STOCH_K"] = stoch.stoch()
    data["STOCH_D"] = stoch.stoch_signal()

    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    data["ADX_14"] = adx.adx()
    data["PLUS_DI"] = adx.adx_pos()
    data["MINUS_DI"] = adx.adx_neg()

    cci = CCIIndicator(high=high, low=low, close=close, window=20)
    data["CCI_20"] = cci.cci()

    willr = WilliamsRIndicator(high=high, low=low, close=close, lbp=14)
    data["WILLIAMS_R"] = willr.williams_r()

    data["ROC_10"] = ROCIndicator(close=close, window=10).roc()
    data["OBV"] = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    data["OBV_SLOPE"] = data["OBV"].diff(5)

    # Session VWAP: reset at each trading date rather than averaging across days.
    typical_price = (high + low + close) / 3.0
    session_key = pd.Series(data.index.date, index=data.index)
    cumulative_pv = (typical_price * volume).groupby(session_key).cumsum()
    cumulative_volume = volume.groupby(session_key).cumsum().mask(lambda s: s == 0)
    data["VWAP"] = cumulative_pv / cumulative_volume

    # Volume ratio versus a 20-period average.
    volume_ma = volume.rolling(20, min_periods=5).mean()
    data["VOLUME_RATIO"] = volume / volume_ma.replace(0, float("nan"))

    return data
