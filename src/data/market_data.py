import yfinance as yf
import pandas as pd


def get_market_data(
    ticker: str,
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Download historical market data for a stock.

    Example:
        TCS.NS
        RELIANCE.NS
        INFY.NS
    """

    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )

    if data.empty:
        raise ValueError(f"No market data found for {ticker}")

    # yfinance can return MultiIndex columns.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    return data