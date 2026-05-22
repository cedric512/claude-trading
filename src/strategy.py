"""
Execution layer: translates portfolio target weights into Alpaca orders.

Strategy: Dual-Momentum + Technical Trend Filter
- Monthly rebalancing to equal-weight top scored stocks
- Stop-loss enforcement at -8% per position
- Sector concentration cap at 30%
"""
import logging
from datetime import date

import pandas as pd

from config.settings import MAX_POSITION_PCT, STOP_LOSS_PCT
from src.portfolio import Portfolio, Position, log_trade, save_portfolio
from src import alpaca_client

logger = logging.getLogger(__name__)


def compute_target_orders(
    portfolio: Portfolio,
    target_selection: pd.DataFrame,
    current_prices: dict[str, float],
) -> dict[str, dict]:
    """
    Return dict of {ticker: {action, qty, price, reason}}.
    Handles: new buys, exits (stop or dropped from selection), partial rebalance.
    """
    total_value = portfolio.total_value
    orders: dict[str, dict] = {}

    # --- 1. Check stop losses on existing positions ---
    portfolio.update_prices(current_prices)
    for ticker in portfolio.get_stops_triggered():
        orders[ticker] = {
            "action": "sell",
            "qty": portfolio.positions[ticker].shares,
            "price": current_prices.get(ticker, 0),
            "reason": f"stop_loss ({portfolio.positions[ticker].pnl_pct*100:.1f}%)",
        }

    # --- 2. Exit positions no longer in target ---
    target_tickers = set(target_selection.index)
    current_tickers = set(portfolio.positions.keys())
    exits = (current_tickers - target_tickers) - {t for t in orders}
    for ticker in exits:
        pos = portfolio.positions[ticker]
        orders[ticker] = {
            "action": "sell",
            "qty": pos.shares,
            "price": current_prices.get(ticker, pos.current_price),
            "reason": "dropped_from_selection",
        }

    # --- 3. Compute buys / top-ups for target tickers ---
    for ticker, row in target_selection.iterrows():
        if ticker in orders:
            continue  # already selling this
        target_value = total_value * row["target_weight"]
        price = current_prices.get(ticker, row.get("current_price", 0))
        if price <= 0:
            continue
        target_shares = target_value / price
        current_shares = portfolio.positions[ticker].shares if ticker in portfolio.positions else 0.0

        delta = target_shares - current_shares
        tolerance = 0.05 * target_shares  # rebalance only if drift > 5%

        if abs(delta) > tolerance and abs(delta) * price > 100:
            orders[ticker] = {
                "action": "buy" if delta > 0 else "sell",
                "qty": abs(delta),
                "price": price,
                "reason": "rebalance" if current_shares > 0 else "initial_buy",
            }

    return orders


def execute_orders(
    portfolio: Portfolio,
    orders: dict[str, dict],
    dry_run: bool = False,
) -> list[dict]:
    """Execute orders via Alpaca (or simulate if dry_run=True)."""
    results = []
    for ticker, order in orders.items():
        action = order["action"]
        qty = round(order["qty"], 4)
        price = order["price"]
        reason = order["reason"]

        if qty <= 0:
            continue

        logger.info("[%s] %s %s x%.4f @ $%.2f (%s)",
                    "DRY" if dry_run else "LIVE", action.upper(), ticker, qty, price, reason)

        if not dry_run:
            try:
                alpaca_client.place_market_order(ticker, qty, action, reason)
            except Exception as e:
                logger.error("Order failed %s: %s", ticker, e)
                results.append({"ticker": ticker, "error": str(e)})
                continue

        # Update local portfolio state
        if action == "sell":
            if ticker in portfolio.positions:
                pos = portfolio.positions[ticker]
                proceeds = qty * price
                portfolio.cash += proceeds
                remaining = pos.shares - qty
                if remaining < 0.001:
                    del portfolio.positions[ticker]
                else:
                    pos.shares = remaining
                log_trade(portfolio, "sell", ticker, qty, price, reason)
        else:  # buy
            cost = qty * price
            if cost > portfolio.cash:
                logger.warning("Insufficient cash for %s: need $%.0f have $%.0f", ticker, cost, portfolio.cash)
                continue
            portfolio.cash -= cost
            if ticker in portfolio.positions:
                pos = portfolio.positions[ticker]
                total_shares = pos.shares + qty
                pos.avg_cost = (pos.shares * pos.avg_cost + qty * price) / total_shares
                pos.shares = total_shares
            else:
                from config.universe import TICKER_SECTOR
                portfolio.positions[ticker] = Position(
                    ticker=ticker,
                    shares=qty,
                    avg_cost=price,
                    current_price=price,
                    sector=TICKER_SECTOR.get(ticker, "Unknown"),
                    entry_date=date.today().isoformat(),
                    stop_loss=round(price * (1 - STOP_LOSS_PCT), 2),
                    target_weight=orders[ticker].get("target_weight", MAX_POSITION_PCT),
                )
            log_trade(portfolio, "buy", ticker, qty, price, reason)

        results.append({"ticker": ticker, "action": action, "qty": qty, "price": price})

    save_portfolio(portfolio)
    return results
