"""
Claude AI market analyst — generates qualitative commentary on the portfolio
and top candidates using the Anthropic API with prompt caching.
"""
import logging
from datetime import date

import anthropic

from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """Tu es un analyste financier senior spécialisé dans les actions américaines du S&P 500 et du Nasdaq 100.
Tu aides à gérer un portefeuille fictif (paper trading) sur un horizon de 6 mois avec une stratégie de momentum dual + filtre technique.

Règles du portefeuille :
- Capital fictif : 100 000 $
- Max 20 positions, pondération égale (≈5% chacune)
- Stop-loss à -8% par position
- Rééquilibrage mensuel
- Univers : S&P 500 + Nasdaq 100

Tu réponds toujours en français, de façon concise et structurée (max 400 mots).
Tu n'inventes pas de données — tu raisonnes à partir des données fournies.
"""


def analyze_weekly(portfolio_summary: dict, top_candidates: list[dict], market_context: str = "") -> str:
    """Generate weekly portfolio analysis narrative."""
    client = get_client()

    positions_text = "\n".join(
        f"- {t}: {p['pnl_pct']:+.1f}% | secteur: {p.get('sector', '?')}"
        for t, p in portfolio_summary.get("positions", {}).items()
    )

    candidates_text = "\n".join(
        f"- {c['ticker']}: score {c.get('score', 0):.0f} | momentum 6M: {c.get('6m', 0)*100:.1f}% | RSI: {c.get('rsi', 0):.0f}"
        for c in top_candidates[:8]
    )

    user_content = f"""Date d'analyse : {date.today().strftime('%d %B %Y')}

PORTEFEUILLE ACTUEL:
Valeur totale : ${portfolio_summary.get('total_value', 0):,.0f}
P&L cumulé : {portfolio_summary.get('total_pnl_pct', 0):+.2f}%
Nombre de positions : {portfolio_summary.get('num_positions', 0)}

POSITIONS EN COURS:
{positions_text or 'Aucune position'}

MEILLEURS CANDIDATS (screening):
{candidates_text or 'Aucun candidat'}

CONTEXTE MARCHÉ:
{market_context or 'Non fourni'}

Génère une analyse hebdomadaire structurée avec :
1. Bilan de la semaine (2-3 phrases)
2. Positions à surveiller (risques ou opportunités)
3. Candidats intéressants à considérer au prochain rééquilibrage
4. Recommandation générale (maintenir / réduire risque / augmenter exposition)
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # cache the system prompt
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text


def analyze_stock(ticker: str, metrics: dict) -> str:
    """Quick qualitative take on a single stock."""
    client = get_client()
    prompt = f"""Donne une analyse rapide (3-4 phrases) de {ticker} :
- Momentum 6M : {metrics.get('6m', 0)*100:.1f}%
- Momentum 3M : {metrics.get('3m', 0)*100:.1f}%
- RSI : {metrics.get('rsi', 0):.0f}
- Score composite : {metrics.get('score', 0):.0f}/100
- Au-dessus MA50 : {metrics.get('above_ma50', False)}
- Au-dessus MA200 : {metrics.get('above_ma200', False)}
- Secteur : {metrics.get('sector', '?')}

Conclusion : est-ce un bon candidat pour un achat moyen terme ? Pourquoi ?"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
