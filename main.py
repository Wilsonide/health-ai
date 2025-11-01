from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cache import (
    add_tip_to_history,
    ensure_cache_exists,
    get_cached_tip_for_today,
    get_history,
)
from openai_client import generate_tip_from_openai
from scheduler import schedule_daily_job, scheduler
from schemas import TelexRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown lifecycle."""
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)


@app.post("/message")
async def message(request: Request):
    """Handles Telex message events and responds intelligently."""
    try:
        payload = await request.json()
        req = TelexRequest(**payload)

        # Extract the latest user message
        message_obj = req.params.message
        parts = message_obj.parts or []
        current_text = (
            parts[-1].text.strip().lower() if parts and parts[-1].text else ""
        )

        if not current_text:
            return JSONResponse(
                {"status": "error", "message": "No user input text found."},
                status_code=400,
            )

        # Normalize & split words
        words = current_text.split()
        command = words[0] if words else ""

        # --- Handle commands based on first keyword ---
        if command in {"refresh", "force", "update"}:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            return {
                "status": "ok",
                "action": "force_refresh",
                "message": tip,
            }

        elif command in {"history", "past", "list"}:
            history = get_history()
            return {
                "status": "ok",
                "action": "get_history",
                "data": history,
            }

        elif command in {"tip", "daily", "get"}:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_openai()
                add_tip_to_history(tip)
            return {
                "status": "ok",
                "action": "get_daily_tip",
                "message": tip,
            }

        # --- Default fallback if no command matched ---
        return {
            "status": "ok",
            "message": (
                "👋 Hey there! Choose an option:\n"
                "• Type **tip** to get your daily fitness advice 💪\n"
                "• Type **refresh** to generate a new one 🔁\n"
                "• Type **history** to view past tips 📜"
            ),
        }

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
