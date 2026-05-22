"""Global configuration for the trading system."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Alpaca ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# --- Anthropic ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Slack ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#trading-signals")

# --- Portfolio parameters ---
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "20"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.05"))   # 5% max per stock
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.08"))         # -8% stop loss
MAX_SECTOR_PCT = 0.30                                               # 30% max per sector

# --- Strategy parameters ---
MOMENTUM_LOOKBACK_DAYS = 126       # 6-month momentum (trading days)
MEDIUM_MA = 50                     # 50-day moving average
LONG_MA = 200                      # 200-day moving average
MIN_AVG_VOLUME_USD = 50_000_000    # $50M average daily volume
MIN_MARKET_CAP = 10_000_000_000    # $10B market cap minimum
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 75

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "momentum_6m": 0.25,      # 6-month price return
    "momentum_3m": 0.15,      # 3-month price return
    "trend_alignment": 0.20,  # Price vs MA50/MA200
    "relative_strength": 0.20, # Return vs SPY
    "volume_trend": 0.10,     # Volume increasing
    "rsi_quality": 0.10,      # RSI not overbought
}

# --- Rebalancing ---
REBALANCE_FREQUENCY = "monthly"    # monthly rebalancing
REBALANCE_DAY = 1                  # 1st trading day of month

# --- Data ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
SIGNALS_FILE = os.path.join(DATA_DIR, "signals_history.json")
SCREENING_FILE = os.path.join(DATA_DIR, "last_screen.json")
