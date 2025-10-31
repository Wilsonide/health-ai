import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from cache import save_tip
from tips import generate_tip

scheduler = BackgroundScheduler()


def daily_job():
    """Generate and store a new daily tip."""
    print("🌅 Running daily tip generation...")
    tip = asyncio.run(generate_tip(force_new=True))
    save_tip(tip)
    print(f"✅ New daily tip generated: {tip}")


def schedule_daily_job():
    """Schedules the daily tip refresh."""
    scheduler.add_job(daily_job, "interval", hours=24)
    scheduler.start()
