"""Send formatted trading summaries to Slack."""
import logging
from datetime import date

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config.settings import SLACK_BOT_TOKEN, SLACK_CHANNEL

logger = logging.getLogger(__name__)

_client: WebClient | None = None


def get_client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient(token=SLACK_BOT_TOKEN)
    return _client


def _post(blocks: list, text: str = "") -> bool:
    try:
        get_client().chat_postMessage(
            channel=SLACK_CHANNEL,
            text=text,
            blocks=blocks,
        )
        return True
    except SlackApiError as e:
        logger.error("Slack error: %s", e.response["error"])
        return False


def _pnl_emoji(pct: float) -> str:
    if pct >= 2:
        return ":chart_with_upwards_trend:"
    if pct >= 0:
        return ":slightly_smiling_face:"
    if pct >= -2:
        return ":slightly_frowning_face:"
    return ":red_circle:"


def send_daily_digest(portfolio_summary: dict, signals: list[dict]) -> bool:
    """Daily end-of-day digest with P&L and top signals."""
    total_pnl_pct = portfolio_summary.get("total_pnl_pct", 0)
    emoji = _pnl_emoji(total_pnl_pct)

    # Build positions table
    positions = portfolio_summary.get("positions", {})
    pos_lines = []
    for ticker, p in sorted(positions.items(), key=lambda x: x[1]["pnl_pct"], reverse=True):
        sign = "+" if p["pnl_pct"] >= 0 else ""
        pos_lines.append(f"• `{ticker}` {sign}{p['pnl_pct']:.1f}% | ${p['market_value']:,.0f}")

    pos_text = "\n".join(pos_lines[:10]) or "_Aucune position_"

    # Top signals
    sig_lines = [
        f"• `{s['ticker']}` score {s['score']:.0f} | mom6m {s.get('6m', 0)*100:.1f}%"
        for s in signals[:5]
    ]
    sig_text = "\n".join(sig_lines) or "_Aucun signal_"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Rapport Journalier — {date.today().strftime('%d %b %Y')}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Valeur totale*\n${portfolio_summary.get('total_value', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*P&L total*\n{'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.2f}%"},
                {"type": "mrkdwn", "text": f"*Cash disponible*\n${portfolio_summary.get('cash', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*Positions*\n{portfolio_summary.get('num_positions', 0)}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Top Positions (P&L)*\n{pos_text}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Meilleurs Signaux du Jour*\n{sig_text}"},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_Claude Trading Bot — portefeuille fictif Alpaca Paper_"}],
        },
    ]
    return _post(blocks, text=f"Rapport trading {date.today().isoformat()}")


def send_weekly_report(portfolio_summary: dict, analysis: str) -> bool:
    """Weekly report with Claude AI analysis."""
    total_pnl_pct = portfolio_summary.get("total_pnl_pct", 0)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bar_chart: Bilan Hebdomadaire — Semaine du {date.today().strftime('%d %b %Y')}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Valeur portefeuille*\n${portfolio_summary.get('total_value', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*Performance cumulée*\n{'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.2f}%"},
                {"type": "mrkdwn", "text": f"*Capital initial*\n${portfolio_summary.get('initial_capital', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*Nb positions*\n{portfolio_summary.get('num_positions', 0)}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Analyse IA de la semaine*\n{analysis}"},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_Analyse générée par Claude Sonnet • Stratégie: Dual Momentum + Trend Filter_"}],
        },
    ]
    return _post(blocks, text="Bilan hebdomadaire du portefeuille")


def send_rebalancing_alert(trades: list[dict], portfolio_summary: dict) -> bool:
    """Alert when rebalancing trades are executed."""
    if not trades:
        return True

    buys = [t for t in trades if t.get("action") == "buy"]
    sells = [t for t in trades if t.get("action") == "sell"]

    buy_lines = "\n".join(f"• :green_circle: BUY `{t['ticker']}` x{t['qty']:.1f} @ ${t['price']:.2f}" for t in buys) or "_Aucun_"
    sell_lines = "\n".join(f"• :red_circle: SELL `{t['ticker']}` x{t['qty']:.1f} @ ${t['price']:.2f}" for t in sells) or "_Aucun_"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":arrows_counterclockwise: Rééquilibrage du Portefeuille"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Achats ({len(buys)})*\n{buy_lines}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Ventes ({len(sells)})*\n{sell_lines}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Valeur totale*\n${portfolio_summary.get('total_value', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*Cash restant*\n${portfolio_summary.get('cash', 0):,.0f}"},
            ],
        },
    ]
    return _post(blocks, text="Rééquilibrage du portefeuille effectué")


def send_stop_loss_alert(tickers: list[str], portfolio_summary: dict) -> bool:
    """Urgent alert when stop losses are triggered."""
    lines = "\n".join(f"• :warning: `{t}`" for t in tickers)
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":rotating_light: Stop-Loss Déclenché"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"Les positions suivantes ont atteint le seuil de -8% :\n{lines}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Cash après clôture*\n${portfolio_summary.get('cash', 0):,.0f}"},
                {"type": "mrkdwn", "text": f"*P&L total*\n{portfolio_summary.get('total_pnl_pct', 0):.2f}%"},
            ],
        },
    ]
    return _post(blocks, text=f"Stop-loss déclenché sur {', '.join(tickers)}")
