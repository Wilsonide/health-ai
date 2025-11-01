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

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- JSON-RPC Endpoint ---
@app.post("/message")
async def message(request: Request):
    """Accepts A2A Telex requests and returns fitness tips."""
    try:
        payload = await request.json()
        req = TelexRequest(**payload)

        message_obj = req.params.message
        parts = message_obj.parts or []

        current_text = ""
        conversation_history = []
        print("my texts: ", parts.text)

        # --- Extract user text (first text part only) ---
        for part in parts:
            if part.kind == "text" and part.text:
                current_text = part.text.strip().lower()
                break  # only first text part needed

        # --- Extract conversation history (if any) ---
        for part in parts:
            if part.kind == "data" and part.data:
                conversation_history = [
                    item.text for item in part.data if getattr(item, "text", None)
                ]
                break

        print(f"🗣️ User Input: {current_text or '[none]'}")
        print(
            f"💬 Conversation history (last {len(conversation_history)} msgs) received."
        )

        if not current_text:
            return JSONResponse(
                {"status": "error", "message": "No valid user input text found."},
                status_code=400,
            )

        # --- Take only the last 5 words of input ---
        words = current_text.split()
        last_five = " ".join(words[-5:])

        print(f"🗣️ Last 5 words from user: {last_five}")

        # --- Command handling ---
        if "history" in last_five:
            history = get_history()
            print("📜 Returning tip history:", history)
            return {"status": "ok", "action": "get_history", "data": history}

        if "refresh" in last_five or "force" in last_five:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            print(f"💡 Refreshed Fitness Tip: {tip}")
            return {"status": "ok", "action": "force_refresh", "message": tip}

        # --- Default: return daily tip ---
        tip = get_cached_tip_for_today()
        if not tip:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)

            print(f"💡 Fitness Tip: {tip}")
            return {"status": "ok", "action": "get_daily_tip", "message": tip}

    except Exception as e:
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
