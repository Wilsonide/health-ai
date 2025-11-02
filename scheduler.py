import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cache import add_tip_to_history, get_cached_tip_for_today
from config import DAILY_TIP_HOUR_UTC
from openai_client import generate_tip_from_gemini

scheduler = AsyncIOScheduler()


async def _scheduled_generate():
    """Generate and cache a new daily fitness tip asynchronously."""
    try:
        existing = get_cached_tip_for_today()
        if existing:
            print("ℹ️ Tip already cached for today — skipping.")
            return

        tip = await generate_tip_from_gemini()
        add_tip_to_history(tip)
        print("✅ Scheduled daily tip generated successfully.")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Scheduled generation failed: {e}")


def schedule_daily_job():
    """Schedules a daily async job using AsyncIOScheduler safely."""
    # Schedule the coroutine directly — APScheduler with AsyncIOScheduler supports async funcs
    scheduler.add_job(
        _scheduled_generate,
        trigger="cron",
        hour=DAILY_TIP_HOUR_UTC,
        minute=0,
        id="daily_tip_job",
        replace_existing=True,
    )

    scheduler.start()
    print("🕒 Daily job scheduled successfully.")
