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
    """Respond to Telex.im events using Telex-compatible message structure."""
    try:
        payload = await request.json()
        req = TelexRequest(**payload)
        request_id = payload.get("id", "no-id")

        message_obj = req.params.message
        parts = message_obj.parts or []

        if not parts or not parts[-1].text:
            return _telex_response(
                request_id,
                "Please send a message so I can generate a tip 💪",
            )

        # Use ONLY the last text from user
        current_text = parts[-1].text.strip().lower()
        print(f"🗣️ Current text from user: {current_text}")

        # Command detection
        if "history" in current_text:
            history = get_history()
            history_text = "\n".join(f"• {h}" for h in history[-10:])
            return _telex_response(request_id, f"📜 Your past tips:\n\n{history_text or 'No tips yet!'}")

        elif "refresh" in current_text or "force" in current_text:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            return _telex_response(request_id, f"🔁 New Fitness Tip:\n\n{tip}")

        elif "tip" in current_text or "daily" in current_text:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_openai()
                add_tip_to_history(tip)
            return _telex_response(request_id, f"💡 Today's Fitness Tip:\n\n{tip}")

        # Default help menu
        return _telex_response(
            request_id,
            (
                "👋 Hi! I'm your AI Fitness Coach!\n\n"
                "Here’s what I can do:\n"
                "• Type **tip** → get your daily health tip 💪\n"
                "• Type **refresh** → get a new one 🔁\n"
                "• Type **history** → see your past tips 📜"
            ),
        )

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": payload.get("id", None),
                "error": {"code": -32000, "message": str(e)},
            },
            status_code=500,
        )


def _telex_response(request_id: str, text: str):
    """Return a valid Telex message/send-compatible response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "message",
            "role": "assistant",
            "parts": [
                {"kind": "text", "text": text}
            ]
        },
    }


@app.get("/")
def root():
    return {
        "name": "Telex AI Fitness Tip Agent",
        "description": "An AI-powered health & fitness agent using OpenAI to generate daily wellness tips.",
        "author": "Wilson Icheku",
        "version": "1.1.0",
        "status": "running",
    }
