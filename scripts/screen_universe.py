"""
Full universe screen — fetches fundamentals + prices for all tickers.
Run once per week (e.g. Sunday evening) to rebuild the scored universe.
Results are cached in data/last_screen.json.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console
from rich.progress import track

from config.universe import ALL_TICKERS, BENCHMARK
from config.settings import SCREENING_FILE, MAX_POSITIONS
from src.market_data import fetch_prices, compute_returns, compute_technicals, fetch_ticker_info
from src.screener import apply_filters, score_universe, select_portfolio

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
console = Console()


def run():
    console.rule("[bold magenta]Full Universe Screen[/bold magenta]")

    # --- Prices (all tickers + benchmark) ---
    console.print(f"[cyan]Downloading prices for {len(ALL_TICKERS)} tickers...[/cyan]")
    tickers = ALL_TICKERS + [BENCHMARK]
    prices = fetch_prices(tickers, period_days=280)

    spy_returns_raw = compute_returns(prices[[BENCHMARK]].rename(columns={BENCHMARK: BENCHMARK}))
    spy_ret_dict = spy_returns_raw.loc[BENCHMARK].to_dict() if BENCHMARK in spy_returns_raw.index else {}

    returns = compute_returns(prices.drop(columns=[BENCHMARK], errors="ignore"))
    technicals = compute_technicals(prices.drop(columns=[BENCHMARK], errors="ignore"))
    console.print(f"[green]Prices computed for {len(returns)} tickers[/green]")

    # --- Fundamentals (slow — one API call per ticker) ---
    console.print("[cyan]Fetching fundamentals (may take a few minutes)...[/cyan]")
    fundamentals: dict[str, dict] = {}
    for ticker in track(ALL_TICKERS, description="Fetching fundamentals..."):
        fundamentals[ticker] = fetch_ticker_info(ticker)

    # --- Screen + score ---
    survivors = apply_filters(returns, technicals, fundamentals)
    scored = score_universe(survivors, technicals, spy_ret_dict)
    selection = select_portfolio(scored, MAX_POSITIONS)

    # --- Save results ---
    os.makedirs(os.path.dirname(SCREENING_FILE), exist_ok=True)
    output = {
        "scored": scored.reset_index().to_dict("records"),
        "selection": selection.reset_index().to_dict("records"),
        "fundamentals": fundamentals,
        "spy_returns": spy_ret_dict,
    }
    with open(SCREENING_FILE, "w") as f:
        json.dump(output, f, indent=2, default=str)
    console.print(f"[green]Screen saved to {SCREENING_FILE}[/green]")

    # --- Summary ---
    console.print(f"\n[bold]Top 20 candidates:[/bold]")
    for _, row in scored.head(20).iterrows():
        console.print(
            f"  {row.name:6s}  score={row['score']:.0f}  6M={row.get('6m', 0)*100:+.1f}%  "
            f"RSI={row.get('rsi', 0):.0f}  {row.get('sector', '?')}"
        )

    console.print(f"\n[bold green]Portfolio selection ({len(selection)} stocks):[/bold green]")
    for _, row in selection.iterrows():
        console.print(f"  {row.name:6s}  weight={row['target_weight']*100:.1f}%  score={row['score']:.0f}")

    return output


if __name__ == "__main__":
    run()
