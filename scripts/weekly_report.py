"""
Weekly report — runs every Monday morning before market open.

Generates a Claude AI narrative analysis + sends to Slack.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console

from config.settings import SCREENING_FILE
from src.portfolio import load_portfolio
from src.analyst import analyze_weekly
from src.slack_reporter import send_weekly_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
console = Console()


def run():
    console.rule("[bold green]Weekly Report[/bold green]")

    portfolio = load_portfolio()
    summary = portfolio.summary_dict()

    # Load top candidates from last screen
    top_candidates: list[dict] = []
    if os.path.exists(SCREENING_FILE):
        with open(SCREENING_FILE) as f:
            screen = json.load(f)
        top_candidates = screen.get("scored", [])[:10]

    # Market context (simple summary from SPY return)
    spy_6m = 0.0
    if top_candidates:
        spy_returns = screen.get("spy_returns", {})
        spy_6m = spy_returns.get("6m", 0.0) or 0.0

    market_context = f"SPY sur 6 mois : {spy_6m*100:+.1f}%"

    console.print("[cyan]Generating Claude AI analysis...[/cyan]")
    analysis = analyze_weekly(summary, top_candidates, market_context)
    console.print(f"\n[italic]{analysis}[/italic]\n")

    sent = send_weekly_report(summary, analysis)
    console.print(f"[green]Weekly report sent to Slack: {sent}[/green]")

    return {"summary": summary, "analysis": analysis}


if __name__ == "__main__":
    run()
