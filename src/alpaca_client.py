"""
Alpaca paper-trading client.
All orders are placed on the paper trading endpoint — no real money involved.
"""
import logging
from datetime import datetime
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

logger = logging.getLogger(__name__)

_trading_client: Optional[TradingClient] = None
_data_client: Optional[StockHistoricalDataClient] = None


def get_trading_client() -> TradingClient:
    global _trading_client
    if _trading_client is None:
        _trading_client = TradingClient(
            ALPACA_API_KEY,
            ALPACA_SECRET_KEY,
            paper=True,
        )
    return _trading_client


def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    return _data_client


def get_account_info() -> dict:
    client = get_trading_client()
    account = client.get_account()
    return {
        "portfolio_value": float(account.portfolio_value),
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
        "equity": float(account.equity),
        "day_trade_count": account.daytrade_count,
        "status": account.status,
    }


def get_positions() -> list[dict]:
    client = get_trading_client()
    positions = client.get_all_positions()
    return [
        {
            "ticker": p.symbol,
            "qty": float(p.qty),
            "avg_cost": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pnl": float(p.unrealized_pl),
            "unrealized_pnl_pct": float(p.unrealized_plpc) * 100,
        }
        for p in positions
    ]


def get_latest_prices(tickers: list[str]) -> dict[str, float]:
    client = get_data_client()
    req = StockLatestQuoteRequest(symbol_or_symbols=tickers)
    quotes = client.get_stock_latest_quote(req)
    return {sym: float(q.ask_price or q.bid_price or 0) for sym, q in quotes.items()}


def place_market_order(
    ticker: str,
    qty: float,
    side: str,
    reason: str = "",
) -> dict:
    """Place a market order. side = 'buy' or 'sell'."""
    client = get_trading_client()
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    req = MarketOrderRequest(
        symbol=ticker,
        qty=qty,
        side=order_side,
        time_in_force=TimeInForce.DAY,
    )
    try:
        order = client.submit_order(req)
        logger.info("[ORDER] %s %s x%.2f — %s", side.upper(), ticker, qty, reason)
        return {
            "id": str(order.id),
            "ticker": ticker,
            "side": side,
            "qty": qty,
            "status": str(order.status),
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        }
    except Exception as e:
        logger.error("Order failed for %s: %s", ticker, e)
        raise


def close_position(ticker: str, reason: str = "") -> dict:
    """Close an existing position entirely."""
    client = get_trading_client()
    try:
        response = client.close_position(ticker)
        logger.info("[CLOSE] %s — %s", ticker, reason)
        return {"ticker": ticker, "status": "closed", "reason": reason}
    except Exception as e:
        logger.error("Failed to close %s: %s", ticker, e)
        raise


def get_open_orders() -> list[dict]:
    client = get_trading_client()
    orders = client.get_orders()
    return [
        {
            "id": str(o.id),
            "ticker": o.symbol,
            "side": str(o.side),
            "qty": float(o.qty or 0),
            "status": str(o.status),
        }
        for o in orders
    ]


def cancel_all_orders() -> None:
    client = get_trading_client()
    client.cancel_orders()
    logger.info("All open orders cancelled.")
