from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from rpc import handle_rpc

from cache import (
    add_tip_to_history,
    ensure_cache_exists,
    get_cached_tip_for_today,
    get_history,
)
from openai_client import generate_tip_from_openai
from scheduler import schedule_daily_job, scheduler
from schemas import DailyTip  # 👈 import scheduler instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown lifecycle:
    - Ensures cache file exists
    - Starts the scheduler
    - Stops it gracefully on shutdown.
    """  # noqa: D205
    # ---- Startup ----
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")

    # Run the application
    yield

    # ---- Shutdown ----
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


# --- FastAPI app instance ---
app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)


# --- JSON-RPC Endpoint ---
@app.post("/message")
async def message(payload: DailyTip):
    try:
        text = payload.text.lower().strip()
        if "history" in text:
            history = get_history()
            return history
        if "refresh" in text or "force" in text:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            return tip
        tip = get_cached_tip_for_today()
        if not tip:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
        return tip  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Error processing message: {e}")
        return JSONResponse(
            {
                "status": "error",
                "message": "Something went wrong. Please try again later.",
                "error": str(e),
            },
            status_code=500,
        )


@app.get("/")
def root():
    return {
        "name": "Telex AI Fitness Tip Agent",
        "short_description": "Provides daily fitness tips via A2A JSON-RPC protocol.",
        "description": (
            "An A2A agent that generates and sends AI-powered daily fitness "
            "tips using JSON-RPC 2.0. Designed for use with Telex workflows."
        ),
        "author": "Wilson Icheku",
        "version": "1.0.0",
        "status": "running",
        "message": "Telex Fitness Agent (REST, OpenAI) is active!",
    }
