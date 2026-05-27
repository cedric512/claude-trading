"""
Trading scheduler — runs all routines at their scheduled CET times.

Schedule:
  screen_universe  : Sunday     20:00 CET  (rebuild scored universe)
  weekly_report    : Monday     08:00 CET  (Claude AI narrative → Slack)
  daily_analysis   : Mon–Fri   22:00 CET  (after US market close)
  rebalance        : 1st biz day/month 09:00 CET  (Alpaca orders)

Usage:
  python scheduler.py            # foreground
  nohup python scheduler.py &    # background (logs to logs/scheduler.log)
"""
import json
import logging
import os
import sys
import time
from datetime import date, datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scheduler.log"),
    ],
)
logger = logging.getLogger(__name__)

CET = pytz.timezone("Europe/Paris")
STATE_FILE = "data/scheduler_state.json"


def _now() -> datetime:
    return datetime.now(CET)


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def _already_ran_today(state: dict, job: str) -> bool:
    return state.get(job) == date.today().isoformat()


def _mark_ran(state: dict, job: str) -> None:
    state[job] = date.today().isoformat()
    _save_state(state)


def _is_first_business_day() -> bool:
    now = _now()
    if now.weekday() >= 5:
        return False
    first = now.replace(day=1)
    while first.weekday() >= 5:
        first = first.replace(day=first.day + 1)
    return first.day == now.day


def _run(name: str, fn) -> None:
    logger.info("=== Starting %s ===", name)
    try:
        fn()
        logger.info("=== %s completed ===", name)
    except Exception as exc:
        logger.error("=== %s FAILED: %s ===", name, exc, exc_info=True)


def _check_and_run() -> None:
    now = _now()
    h = now.hour
    wd = now.weekday()  # 0=Mon … 6=Sun
    state = _load_state()

    # screen_universe — Sunday 20:00 CET
    if wd == 6 and h == 20 and not _already_ran_today(state, "screen"):
        from scripts.screen_universe import run
        _run("screen_universe", run)
        _mark_ran(state, "screen")

    # weekly_report — Monday 08:00 CET
    if wd == 0 and h == 8 and not _already_ran_today(state, "weekly"):
        from scripts.weekly_report import run
        _run("weekly_report", run)
        _mark_ran(state, "weekly")

    # daily_analysis — Mon–Fri 22:00 CET
    if wd <= 4 and h == 22 and not _already_ran_today(state, "daily"):
        from scripts.daily_analysis import run
        _run("daily_analysis", run)
        _mark_ran(state, "daily")

    # rebalance — 1st business day of month 09:00 CET
    if h == 9 and _is_first_business_day() and not _already_ran_today(state, "rebalance"):
        from scripts.rebalance import run
        _run("rebalance", run)
        _mark_ran(state, "rebalance")


if __name__ == "__main__":
    logger.info("Scheduler started — timezone: Europe/Paris (CET/CEST)")
    logger.info("  screen_universe  : Sunday 20:00 CET")
    logger.info("  weekly_report    : Monday 08:00 CET")
    logger.info("  daily_analysis   : Mon–Fri 22:00 CET")
    logger.info("  rebalance        : 1st business day/month 09:00 CET")

    while True:
        try:
            _check_and_run()
        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc, exc_info=True)
        time.sleep(30)
