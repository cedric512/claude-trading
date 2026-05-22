"""
Stock screener: applies filters then scores each ticker 0–100.

Scoring model (weights defined in config/settings.py):
  - momentum_6m:       6-month price return
  - momentum_3m:       3-month price return
  - trend_alignment:   price position vs MA50 / MA200
  - relative_strength: 6-month return vs SPY benchmark
  - volume_trend:      increasing vs decreasing volume
  - rsi_quality:       RSI not overbought (penalty above 70)
"""
import logging

import numpy as np
import pandas as pd

from config.settings import (
    MIN_AVG_VOLUME_USD,
    MIN_MARKET_CAP,
    MAX_POSITIONS,
    SCORE_WEIGHTS,
    RSI_OVERBOUGHT,
)
from config.universe import TICKER_SECTOR

logger = logging.getLogger(__name__)


def _minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def apply_filters(
    returns: pd.DataFrame,
    technicals: pd.DataFrame,
    fundamentals: dict[str, dict],
    min_volume_usd: float = MIN_AVG_VOLUME_USD,
    min_market_cap: float = MIN_MARKET_CAP,
) -> pd.DataFrame:
    """Remove tickers that fail hard filters; return survivors."""
    passing = []
    for ticker in returns.index:
        info = fundamentals.get(ticker, {})
        price = returns.loc[ticker, "current_price"] if "current_price" in returns.columns else np.nan

        # Liquidity: average daily volume in USD
        avg_vol = info.get("avg_volume", 0) or 0
        avg_vol_usd = avg_vol * price if (price and price > 0) else 0

        # Market cap
        mkt_cap = info.get("market_cap", 0) or 0

        # Must be above 200-day MA (uptrend)
        above_200 = technicals.loc[ticker, "above_ma200"] if ticker in technicals.index else False

        if avg_vol_usd >= min_volume_usd and mkt_cap >= min_market_cap and above_200:
            passing.append(ticker)
        else:
            reason = []
            if avg_vol_usd < min_volume_usd:
                reason.append(f"low_vol({avg_vol_usd/1e6:.0f}M)")
            if mkt_cap < min_market_cap:
                reason.append(f"small_cap({mkt_cap/1e9:.1f}B)")
            if not above_200:
                reason.append("below_MA200")
            logger.debug("Filtered out %s: %s", ticker, ", ".join(reason))

    logger.info("Filters passed: %d / %d tickers", len(passing), len(returns))
    return returns.loc[passing]


def score_universe(
    returns: pd.DataFrame,
    technicals: pd.DataFrame,
    spy_returns: dict,
) -> pd.DataFrame:
    """Score each surviving ticker and return ranked DataFrame."""
    df = returns.copy()
    tech = technicals.reindex(df.index)
    w = SCORE_WEIGHTS

    # --- Individual sub-scores (0–1 each) ---

    # 6M momentum
    m6 = df["6m"].fillna(-1)
    spy_6m = spy_returns.get("6m", 0)
    s_mom6 = _minmax(m6)

    # 3M momentum
    m3 = df["3m"].fillna(-1)
    s_mom3 = _minmax(m3)

    # Trend alignment: above MA50 (+0.5) + above MA200 (+0.5)
    above50 = tech["above_ma50"].fillna(False).astype(float)
    above200 = tech["above_ma200"].fillna(False).astype(float)
    s_trend = (above50 * 0.5 + above200 * 0.5)

    # Relative strength vs SPY (6M)
    rel = m6 - spy_6m
    s_rel = _minmax(rel)

    # RSI quality: penalise overbought
    rsi = tech["rsi"].fillna(50)
    s_rsi = rsi.apply(lambda r: max(0, 1 - max(0, r - RSI_OVERBOUGHT) / (100 - RSI_OVERBOUGHT)))

    # Volume trend: use 3M vs 6M return spread as proxy for acceleration
    accel = df["3m"].fillna(0) - df["6m"].fillna(0) / 2
    s_vol = _minmax(accel)

    # --- Weighted composite score ---
    score = (
        w["momentum_6m"] * s_mom6
        + w["momentum_3m"] * s_mom3
        + w["trend_alignment"] * s_trend
        + w["relative_strength"] * s_rel
        + w["volume_trend"] * s_vol
        + w["rsi_quality"] * s_rsi
    )

    result = df.copy()
    result["score"] = (score * 100).round(1)
    result["rsi"] = rsi
    result["above_ma50"] = above50.astype(bool)
    result["above_ma200"] = above200.astype(bool)
    result["sector"] = [TICKER_SECTOR.get(t, "Unknown") for t in result.index]
    result["rel_vs_spy"] = (m6 - spy_6m).round(4)

    return result.sort_values("score", ascending=False)


def select_portfolio(scored: pd.DataFrame, max_positions: int = MAX_POSITIONS) -> pd.DataFrame:
    """
    Pick top stocks respecting sector concentration limit.
    Returns the final selection with target weights.
    """
    from config.settings import MAX_SECTOR_PCT

    selected = []
    sector_count: dict[str, int] = {}

    for ticker, row in scored.iterrows():
        sector = row["sector"]
        sector_slots = int(max_positions * MAX_SECTOR_PCT)
        if sector_count.get(sector, 0) >= sector_slots:
            logger.debug("Sector cap reached for %s, skipping %s", sector, ticker)
            continue
        selected.append(ticker)
        sector_count[sector] = sector_count.get(sector, 0) + 1
        if len(selected) >= max_positions:
            break

    result = scored.loc[selected].copy()
    result["target_weight"] = round(1.0 / len(result), 4)
    logger.info("Portfolio: %d positions selected", len(result))
    return result
