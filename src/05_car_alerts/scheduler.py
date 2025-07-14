"""
Start APScheduler with a single cron job at 06:00 Europe/Berlin daily.
Call this script once (e.g. via systemd or docker) and it keeps running.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from orchestrator import run_daily_job

def start():
    berlin = timezone("Europe/Berlin")
    sched  = BlockingScheduler(timezone=berlin)

    sched.add_job(
        run_daily_job,
        trigger=CronTrigger(hour=6, minute=0, timezone=berlin),
        id="daily_autobid_scrape",
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )

    print("⏰ Scheduler started – waiting for 06:00 …")
    sched.start()

if __name__ == "__main__":
    start()
