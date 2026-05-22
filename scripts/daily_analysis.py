"""
Daily analysis routine — runs every trading day after market close (≈ 22h00 CET).

Steps:
  1. Fetch latest prices for all universe tickers
  2. Update portfolio prices + check stop losses
  3. Run screener to get top signals
  4. Send Slack digest
  5. Save updated portfolio
"""
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console
from rich.table import Table

from config.universe import ALL_TICKERS, BENCHMARK
from config.settings import MAX_POSITIONS
from src.market_data import fetch_prices, compute_returns, compute_technicals, fetch_ticker_info
from src.screener import apply_filters, score_universe, select_portfolio
from src.portfolio import load_portfolio, save_portfolio
from src.slack_reporter import send_daily_digest, send_stop_loss_alert

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)
console = Console()


def run():
    console.rule("[bold blue]Daily Analysis[/bold blue]")

    # --- 1. Fetch prices ---
    console.print("[cyan]Fetching prices...[/cyan]")
    tickers = ALL_TICKERS + [BENCHMARK]
    prices = fetch_prices(tickers, period_days=252)

    # --- 2. Compute returns & technicals ---
    returns = compute_returns(prices.drop(columns=[BENCHMARK], errors="ignore"))
    spy_returns = compute_returns(prices[[BENCHMARK]].rename(columns={BENCHMARK: BENCHMARK}))
    spy_ret_dict = spy_returns.loc[BENCHMARK].to_dict() if BENCHMARK in spy_returns.index else {}
    technicals = compute_technicals(prices.drop(columns=[BENCHMARK], errors="ignore"))

    console.print(f"[green]Got data for {len(returns)} tickers[/green]")

    # --- 3. Lightweight fundamentals (cached, only re-fetched weekly) ---
    import json
    from config.settings import SCREENING_FILE
    fundamentals: dict = {}
    if os.path.exists(SCREENING_FILE):
        with open(SCREENING_FILE) as f:
            fundamentals = json.load(f).get("fundamentals", {})

    # --- 4. Screen + score ---
    survivors = apply_filters(returns, technicals, fundamentals)
    scored = score_universe(survivors, technicals, spy_ret_dict)
    top_candidates = scored.head(MAX_POSITIONS * 2).reset_index().to_dict("records")

    # --- 5. Load portfolio, update prices, check stops ---
    portfolio = load_portfolio()
    current_prices = {t: returns.loc[t, "current_price"] for t in portfolio.positions if t in returns.index}
    portfolio.update_prices(current_prices)

    stops = portfolio.get_stops_triggered()
    if stops:
        console.print(f"[red]Stop-loss triggered: {stops}[/red]")
        save_portfolio(portfolio)
        send_stop_loss_alert(stops, portfolio.summary_dict())

    # --- 6. Print top signals ---
    table = Table(title="Top 10 Signals", show_header=True)
    table.add_column("Ticker", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("6M%", justify="right")
    table.add_column("RSI", justify="right")
    table.add_column("Sector")
    for row in top_candidates[:10]:
        table.add_row(
            row["ticker"],
            f"{row['score']:.0f}",
            f"{row.get('6m', 0)*100:+.1f}%",
            f"{row.get('rsi', 0):.0f}",
            row.get("sector", "?"),
        )
    console.print(table)

    # --- 7. Slack digest ---
    sent = send_daily_digest(portfolio.summary_dict(), top_candidates[:5])
    console.print(f"[green]Slack digest sent: {sent}[/green]")

    # --- 8. Save ---
    save_portfolio(portfolio)
    console.print("[bold green]Daily analysis complete.[/bold green]")

    return {"portfolio": portfolio.summary_dict(), "top_candidates": top_candidates}


if __name__ == "__main__":
    run()
