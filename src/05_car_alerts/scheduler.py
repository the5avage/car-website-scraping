"""
Start APScheduler with a single cron job at HH:MM Europe/Berlin daily.
Call this script once (e.g. systemd / Docker) and it keeps running.
"""

# standard library
import argparse
import logging
import sys

# third party libraries
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# project imports
from orchestrator import run_daily_job


# ------------------------------------------------------------------ #
#  CLI argument parsing
# ------------------------------------------------------------------ #
def parse_cli():
    p = argparse.ArgumentParser(description="Daily scraper scheduler")
    p.add_argument(
        "-H", "--hour", type=int, default=6, help="Hour of day (0‑23)  [default: 6]"
    )
    p.add_argument(
        "-M", "--minute", type=int, default=0, help="Minute (0‑59)       [default: 0]"
    )
    args = p.parse_args()

    # Simple range validation
    if not (0 <= args.hour <= 23):
        p.error("hour must be in 0‑23")
    if not (0 <= args.minute <= 59):
        p.error("minute must be in 0‑59")
    return args.hour, args.minute


# ------------------------------------------------------------------ #
#  Scheduler bootstrap
# ------------------------------------------------------------------ #
def start(hour: int, minute: int, log: logging.Logger):
    berlin = timezone("Europe/Berlin")
    sched = BlockingScheduler(timezone=berlin)

    trigger = CronTrigger(hour=hour, minute=minute, timezone=berlin)

    sched.add_job(
        run_daily_job,
        trigger=trigger,
        id="daily_autobid_scrape",
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )

    log.info("Scheduler started – waiting for %02d:%02d Europe/Berlin …", hour, minute)
    sched.start()


# ------------------------------------------------------------------ #
if __name__ == "__main__":

    log = logging.getLogger("Scheduler")
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter(
                "[Scheduler]: %(asctime)s  %(levelname)s  %(message)s", "%H:%M:%S"
            )
        )
        log.addHandler(h)
        log.setLevel(logging.INFO)

    h, m = parse_cli()
    start(h, m, log)
