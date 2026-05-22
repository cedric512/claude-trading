# Claude Trading — Guide du projet

## Vue d'ensemble

Portefeuille fictif de 100 000 $ investis dans des actions du S&P 500 et du Nasdaq 100,
géré algorithmiquement via **Alpaca Paper Trading** avec des rapports **Slack** automatisés.

**Stratégie** : Dual Momentum + Filtre Technique (MA50/MA200)
**Horizon** : 6 mois | **Rééquilibrage** : mensuel | **Positions** : max 20 | **Stop-loss** : -8%

---

## Configuration initiale

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Variables d'environnement

Copier `.env.example` en `.env` et remplir :

```bash
cp .env.example .env
```

| Variable | Où la trouver |
|---|---|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | alpaca.markets → Paper Trading |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `SLACK_BOT_TOKEN` | api.slack.com → Apps → Bot Token |
| `SLACK_CHANNEL` | `#nom-du-canal` dans ton workspace |

---

## Routines (ordre d'exécution)

### Étape 1 — Screening hebdomadaire (dimanche soir)

```bash
python scripts/screen_universe.py
```

Analyse ~170 actions (S&P 500 + Nasdaq 100), calcule les scores de momentum,
filtre par liquidité/capitalisation/tendance, et sauvegarde le résultat dans
`data/last_screen.json`.

**Durée** : ~5-10 min (appels yfinance pour les fondamentaux).

---

### Étape 2 — Rééquilibrage mensuel (1er jour ouvré du mois)

```bash
# Simuler d'abord (pas d'ordres réels)
python scripts/rebalance.py --dry-run

# Exécuter sur Alpaca Paper
python scripts/rebalance.py
```

Lit `data/last_screen.json`, calcule les ordres à passer, les exécute sur Alpaca
et envoie une alerte Slack.

---

### Étape 3 — Analyse quotidienne (après clôture US, ≈ 22h CET)

```bash
python scripts/daily_analysis.py
```

Met à jour les prix, vérifie les stop-loss, calcule les top signaux du jour
et envoie le digest Slack.

---

### Étape 4 — Rapport hebdomadaire (lundi matin)

```bash
python scripts/weekly_report.py
```

Génère une analyse narrative via Claude AI et l'envoie sur Slack.

---

## Utiliser les routines Claude Code (`/loop`)

Pour automatiser une tâche récurrente dans cette session Claude Code :

```
/loop 1d python scripts/daily_analysis.py
```

Exemples :
- `/loop 1d python scripts/daily_analysis.py` — analyse quotidienne
- `/loop 7d python scripts/weekly_report.py` — rapport hebdo
- `/loop 30d python scripts/rebalance.py` — rééquilibrage mensuel

---

## Structure du projet

```
claude-trading/
├── config/
│   ├── settings.py        # Paramètres globaux (chargés depuis .env)
│   └── universe.py        # Univers S&P500 + Nasdaq100 (~170 tickers)
├── src/
│   ├── market_data.py     # Fetch prix + indicateurs techniques (yfinance)
│   ├── screener.py        # Scoring composite 0-100
│   ├── strategy.py        # Calcul des ordres + exécution
│   ├── portfolio.py       # État du portefeuille (chargement/sauvegarde)
│   ├── alpaca_client.py   # Client Alpaca Paper Trading
│   ├── slack_reporter.py  # Rapports Slack formatés
│   └── analyst.py         # Analyse narrative Claude AI
├── scripts/
│   ├── screen_universe.py # Screening hebdo de l'univers complet
│   ├── daily_analysis.py  # Routine quotidienne post-clôture
│   ├── weekly_report.py   # Rapport hebdomadaire avec IA
│   └── rebalance.py       # Rééquilibrage mensuel Alpaca
├── data/
│   ├── portfolio.json     # État du portefeuille (auto-généré)
│   ├── last_screen.json   # Dernier screening (auto-généré)
│   └── signals_history.json
└── .env                   # Variables d'environnement (ne pas committer)
```

---

## Modèle de scoring (0–100)

| Critère | Poids | Description |
|---|---|---|
| Momentum 6 mois | 25% | Performance des 6 derniers mois |
| Momentum 3 mois | 15% | Performance des 3 derniers mois |
| Alignement technique | 20% | Prix au-dessus MA50 + MA200 |
| Force relative vs SPY | 20% | Surperformance par rapport au marché |
| Tendance volume | 10% | Accélération du momentum |
| Qualité RSI | 10% | Pénalité si RSI > 75 (surachat) |

---

## Filtres d'éligibilité (avant scoring)

- Volume quotidien moyen > 50 M$ (liquidité suffisante)
- Capitalisation boursière > 10 Md$ (large caps uniquement)
- Prix au-dessus de la MA200 (tendance haussière requise)

---

## Gestion des risques

| Règle | Valeur |
|---|---|
| Stop-loss par position | -8% |
| Poids max par position | 5% du portefeuille |
| Poids max par secteur | 30% du portefeuille |
| Rééquilibrage si dérive | > 5% du poids cible |

---

## Messages Slack envoyés

| Rapport | Déclencheur | Contenu |
|---|---|---|
| Digest quotidien | Fin de séance | P&L, top positions, top signaux |
| Rapport hebdomadaire | Lundi matin | Analyse narrative Claude AI |
| Alerte rééquilibrage | 1er du mois | Liste des trades passés |
| Alerte stop-loss | En temps réel | Positions fermées d'urgence |

---

## Commandes utiles

```bash
# Voir l'état du portefeuille
python -c "from src.portfolio import load_portfolio; p = load_portfolio(); print(p.summary_dict())"

# Vérifier la connexion Alpaca
python -c "from src.alpaca_client import get_account_info; print(get_account_info())"

# Voir les positions Alpaca en direct
python -c "from src.alpaca_client import get_positions; print(get_positions())"

# Tester l'envoi Slack
python -c "from src.slack_reporter import send_daily_digest; send_daily_digest({'total_value': 100000, 'total_pnl_pct': 0, 'cash': 100000, 'num_positions': 0, 'positions': {}}, [])"
```
