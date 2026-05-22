# Claude Trading

![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)
![Statut](https://img.shields.io/badge/statut-actif-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

Système de trading algorithmique sur le **S&P 500 et le Nasdaq 100** —
portefeuille fictif géré via **Alpaca Paper Trading**, avec rapports automatiques sur **Slack**
et analyse narrative par **Claude AI**.

## Stratégie

**Dual Momentum + Filtre Technique** — horizon 6 mois

- Univers : ~170 grandes capitalisations (S&P 500 + Nasdaq 100)
- Scoring composite : momentum 6M/3M, alignement MA50/MA200, force relative, RSI
- Max 20 positions — pondération égale (5% chacune)
- Stop-loss à -8% | Rééquilibrage mensuel | Concentration sectorielle max 30%

## Démarrage rapide

```bash
git clone https://github.com/cedric512/claude-trading.git
cd claude-trading
pip install -r requirements.txt
cp .env.example .env   # remplir les clés API
```

Voir [CLAUDE.md](CLAUDE.md) pour la documentation complète.

## Routines

| Fréquence | Script | Description |
|---|---|---|
| Hebdomadaire | `screen_universe.py` | Scoring de l'univers complet |
| Mensuel | `rebalance.py` | Rééquilibrage via Alpaca Paper |
| Quotidien | `daily_analysis.py` | P&L + signaux + digest Slack |
| Hebdomadaire | `weekly_report.py` | Rapport narratif Claude AI |

## Licence

MIT
