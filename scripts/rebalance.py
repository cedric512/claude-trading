"""
Monthly rebalancing script — runs on the 1st trading day of each month.

Steps:
  1. Load last screen results (from screen_universe.py)
  2. Compute target orders vs current portfolio
  3. Execute orders on Alpaca paper trading
  4. Send Slack rebalancing alert
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console

from config.settings import SCREENING_FILE, MAX_POSITIONS
from src.portfolio import load_portfolio, save_portfolio
from src.strategy import compute_target_orders, execute_orders
from src.slack_reporter import send_rebalancing_alert

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
console = Console()


def run(dry_run: bool = False):
    console.rule(f"[bold yellow]Monthly Rebalance {'(DRY RUN)' if dry_run else ''}[/bold yellow]")

    # --- Load last screen ---
    if not os.path.exists(SCREENING_FILE):
        console.print("[red]No screen file found. Run screen_universe.py first.[/red]")
        sys.exit(1)

    with open(SCREENING_FILE) as f:
        screen = json.load(f)

    import pandas as pd
    selection = pd.DataFrame(screen["selection"]).set_index("ticker") if screen.get("selection") else pd.DataFrame()

    if selection.empty:
        console.print("[red]Empty selection in screen file.[/red]")
        sys.exit(1)

    console.print(f"[cyan]Target portfolio: {len(selection)} stocks[/cyan]")

    # --- Current portfolio ---
    portfolio = load_portfolio()
    console.print(f"[cyan]Current portfolio: {len(portfolio.positions)} positions, "
                  f"${portfolio.total_value:,.0f} total value[/cyan]")

    # --- Current prices from screen (fallback) ---
    current_prices: dict[str, float] = {}
    for row in screen.get("selection", []):
        t = row.get("ticker") or row.get("index")
        p = row.get("current_price", 0)
        if t and p:
            current_prices[t] = float(p)

    # Also get prices for existing positions not in selection
    for row in screen.get("scored", []):
        t = row.get("ticker") or row.get("index")
        p = row.get("current_price", 0)
        if t and p and t not in current_prices:
            current_prices[t] = float(p)

    # --- Compute orders ---
    orders = compute_target_orders(portfolio, selection, current_prices)

    if not orders:
        console.print("[green]Portfolio already balanced — no trades needed.[/green]")
        return []

    console.print(f"\n[bold]Planned trades ({len(orders)}):[/bold]")
    for ticker, order in orders.items():
        sign = "+" if order["action"] == "buy" else "-"
        console.print(f"  {sign}{ticker:6s} {order['action'].upper():4s} "
                      f"x{order['qty']:.2f} @ ${order['price']:.2f} ({order['reason']})")

    if dry_run:
        console.print("\n[yellow]DRY RUN — no orders submitted.[/yellow]")
        return list(orders.values())

    # --- Execute ---
    results = execute_orders(portfolio, orders, dry_run=False)
    console.print(f"\n[green]Executed {len(results)} trades.[/green]")

    # --- Slack alert ---
    send_rebalancing_alert(results, portfolio.summary_dict())

    # --- Summary ---
    console.print(f"\n[bold]Portfolio after rebalance:[/bold]")
    console.print(f"  Total value: ${portfolio.total_value:,.0f}")
    console.print(f"  Cash: ${portfolio.cash:,.0f}")
    console.print(f"  Positions: {len(portfolio.positions)}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate without placing orders")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
