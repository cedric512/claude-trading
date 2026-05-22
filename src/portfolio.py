"""Portfolio state management — load, save, compute P&L."""
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from typing import Optional

import pandas as pd

from config.settings import INITIAL_CAPITAL, PORTFOLIO_FILE, STOP_LOSS_PCT

logger = logging.getLogger(__name__)


@dataclass
class Position:
    ticker: str
    shares: float
    avg_cost: float
    sector: str
    entry_date: str
    stop_loss: float = 0.0
    current_price: float = 0.0
    target_weight: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def pnl(self) -> float:
        return self.shares * (self.current_price - self.avg_cost)

    @property
    def pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost

    @property
    def stop_triggered(self) -> bool:
        return self.pnl_pct <= -STOP_LOSS_PCT


@dataclass
class Portfolio:
    cash: float = INITIAL_CAPITAL
    initial_capital: float = INITIAL_CAPITAL
    positions: dict[str, Position] = field(default_factory=dict)
    trade_log: list[dict] = field(default_factory=list)
    inception_date: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def total_value(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        return self.total_value - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        return self.total_pnl / self.initial_capital

    def update_prices(self, prices: dict[str, float]) -> None:
        for ticker, pos in self.positions.items():
            if ticker in prices:
                pos.current_price = prices[ticker]

    def get_stops_triggered(self) -> list[str]:
        return [t for t, p in self.positions.items() if p.stop_triggered]

    def summary_dict(self) -> dict:
        return {
            "date": date.today().isoformat(),
            "total_value": round(self.total_value, 2),
            "cash": round(self.cash, 2),
            "initial_capital": self.initial_capital,
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct * 100, 2),
            "num_positions": len(self.positions),
            "positions": {
                t: {
                    "shares": round(p.shares, 4),
                    "avg_cost": round(p.avg_cost, 2),
                    "current_price": round(p.current_price, 2),
                    "market_value": round(p.market_value, 2),
                    "pnl": round(p.pnl, 2),
                    "pnl_pct": round(p.pnl_pct * 100, 2),
                    "sector": p.sector,
                    "entry_date": p.entry_date,
                    "stop_loss": round(p.stop_loss, 2),
                }
                for t, p in self.positions.items()
            },
        }


def load_portfolio() -> Portfolio:
    if not os.path.exists(PORTFOLIO_FILE):
        logger.info("No portfolio file found, creating fresh portfolio.")
        return Portfolio()
    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)
    portfolio = Portfolio(
        cash=data["cash"],
        initial_capital=data.get("initial_capital", INITIAL_CAPITAL),
        inception_date=data.get("inception_date", date.today().isoformat()),
        trade_log=data.get("trade_log", []),
    )
    for ticker, pd_data in data.get("positions", {}).items():
        portfolio.positions[ticker] = Position(
            ticker=ticker,
            shares=pd_data["shares"],
            avg_cost=pd_data["avg_cost"],
            current_price=pd_data.get("current_price", pd_data["avg_cost"]),
            sector=pd_data.get("sector", "Unknown"),
            entry_date=pd_data.get("entry_date", date.today().isoformat()),
            stop_loss=pd_data.get("stop_loss", 0.0),
            target_weight=pd_data.get("target_weight", 0.0),
        )
    return portfolio


def save_portfolio(portfolio: Portfolio) -> None:
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    data = {
        "cash": portfolio.cash,
        "initial_capital": portfolio.initial_capital,
        "inception_date": portfolio.inception_date,
        "trade_log": portfolio.trade_log[-200:],  # keep last 200 trades
        "positions": {
            t: {
                "shares": p.shares,
                "avg_cost": p.avg_cost,
                "current_price": p.current_price,
                "sector": p.sector,
                "entry_date": p.entry_date,
                "stop_loss": p.stop_loss,
                "target_weight": p.target_weight,
            }
            for t, p in portfolio.positions.items()
        },
    }
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Portfolio saved to %s", PORTFOLIO_FILE)


def log_trade(
    portfolio: Portfolio,
    action: str,
    ticker: str,
    shares: float,
    price: float,
    reason: str = "",
) -> None:
    portfolio.trade_log.append({
        "date": datetime.utcnow().isoformat(),
        "action": action,
        "ticker": ticker,
        "shares": round(shares, 4),
        "price": round(price, 2),
        "value": round(shares * price, 2),
        "reason": reason,
    })
