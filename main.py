from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
    """Handle startup and shutdown lifecycle."""
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


# --- FastAPI app instance ---
app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with a list like ["https://telex.im"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- JSON-RPC Endpoint ---
@app.post("/message")
async def message(request: Request):
    """Main endpoint — accepts user input and returns AI-generated tips."""
    try:
        payload = await request.json()
        req = TelexRequest(**payload)

        message_obj = req.params.message
        parts = message_obj.parts or []

        current_text = ""
        conversation_history = []

        # --- Extract current user intent (index 0) and conversation data (index 1) ---
        if len(parts) >= 1 and parts[0].kind == "text":
            current_text = parts[0].text.strip().lower()

        if len(parts) >= 2 and parts[1].kind == "data":
            data_part = parts[1].data
            if isinstance(data_part, list):
                conversation_history = [
                    item.get("text", "") for item in data_part if isinstance(item, dict)
                ]

        print(f"🗣️ User Input: {current_text}")
        print(
            f"💬 Conversation history (last {len(conversation_history)} msgs) received."
        )

        if not current_text:
            return JSONResponse(
                {"status": "error", "message": "No valid user input text found."},
                status_code=400,
            )

        print(f"🗣️ Last 5 words from user: {current_text}")

        # --- Command handling ---
        if "history" in current_text:
            history = get_history()
            print("📜 Returning tip history:", history)
            return {
                "status": "ok",
                "action": "get_history",
                "data": history,
            }

        if "refresh" in current_text or "force" in current_text:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            print(f"💡 Fitness Tip: {tip}")
            return {
                "status": "ok",
                "action": "force_refresh",
                "message": tip,
            }

        tip = get_cached_tip_for_today()
        if not tip:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)

            print(f"💡 Fitness Tip: {tip}")
            return {
                "status": "ok",
                "action": "get_daily_tip",
                "message": tip,
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
