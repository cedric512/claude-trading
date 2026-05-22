"""Fetch and cache OHLCV + fundamental data via yfinance."""
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_prices(tickers: list[str], period_days: int = 252) -> pd.DataFrame:
    """Return adjusted-close price DataFrame indexed by date."""
    end = datetime.today()
    start = end - timedelta(days=period_days + 30)  # buffer for MA calculation
    raw = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]]
    return prices.dropna(how="all")


def fetch_ticker_info(ticker: str) -> dict:
    """Return key fundamental fields for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker,
            "market_cap": info.get("marketCap", 0),
            "avg_volume": info.get("averageDailyVolume10Day", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "name": info.get("longName", ticker),
        }
    except Exception as e:
        logger.warning("Could not fetch info for %s: %s", ticker, e)
        return {"ticker": ticker, "market_cap": 0, "avg_volume": 0}


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of cumulative returns for key lookback windows."""
    results = {}
    for col in prices.columns:
        s = prices[col].dropna()
        if len(s) < 30:
            continue
        ret = {}
        for days, label in [(21, "1m"), (63, "3m"), (126, "6m"), (252, "12m")]:
            if len(s) > days:
                ret[label] = (s.iloc[-1] / s.iloc[-days] - 1)
            else:
                ret[label] = np.nan
        ret["current_price"] = s.iloc[-1]
        results[col] = ret
    return pd.DataFrame(results).T


def compute_technicals(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute MA50, MA200, RSI, and volume trend for each ticker."""
    from ta.momentum import RSIIndicator

    rows = []
    for col in prices.columns:
        s = prices[col].dropna()
        if len(s) < 200:
            rows.append({"ticker": col, "ma50": np.nan, "ma200": np.nan,
                         "rsi": np.nan, "above_ma50": False, "above_ma200": False})
            continue
        ma50 = s.rolling(50).mean().iloc[-1]
        ma200 = s.rolling(200).mean().iloc[-1]
        rsi = RSIIndicator(s, window=14).rsi().iloc[-1]
        price = s.iloc[-1]
        rows.append({
            "ticker": col,
            "ma50": ma50,
            "ma200": ma200,
            "rsi": rsi,
            "above_ma50": price > ma50,
            "above_ma200": price > ma200,
            "current_price": price,
        })
    return pd.DataFrame(rows).set_index("ticker")
