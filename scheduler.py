import asyncio
import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cache import add_tip_to_history, get_cached_tip_for_today
from config import DAILY_TIP_HOUR_UTC
from openai_client import generate_tip_from_openai

scheduler = AsyncIOScheduler()


async def _scheduled_generate():
    try:
        existing = get_cached_tip_for_today()
        if existing:
            # already present, skip generation to preserve same-tip-per-day behavior
            print(
                f"[{datetime.datetime.utcnow().isoformat()}] Tip already cached for today."  # noqa: DTZ003
            )
            return
        tip = await generate_tip_from_openai()
        add_tip_to_history(tip)
        print(
            f"[{datetime.datetime.utcnow().isoformat()}] Scheduled tip generated:",
            tip,  # noqa: DTZ003
        )
    except Exception as e:  # noqa: BLE001
        print("Scheduled generation failed:", e)


def schedule_daily_job():
    # Cron: run daily at DAILY_TIP_HOUR_UTC:00 UTC
    scheduler.add_job(
        func=lambda: asyncio.create_task(_scheduled_generate()),
        trigger="cron",
        hour=DAILY_TIP_HOUR_UTC,
        minute=0,
        id="daily_tip_job",
        replace_existing=True,
    )
    scheduler.start()
