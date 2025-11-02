import re
from contextlib import asynccontextmanager

import httpx
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


app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean_text(text: str) -> str:
    """Remove HTML tags and trim whitespace."""
    return re.sub(r"<.*?>", "", text or "").strip()


@app.post("/message")
async def message(request: Request):
    """Accepts A2A Telex requests and returns fitness tips to the chatbox."""
    try:
        payload = await request.json()
        print("📩 Incoming payload:", payload)

        params = payload.get("params", {})
        message_obj = params.get("message", {})
        parts = message_obj.get("parts", [])

        current_text = ""
        response_text = ""

        if parts:
            # 1️⃣ Prefer the first text part if present and non-empty
            if parts[0].get("kind") == "text" and parts[0].get("text", "").strip():
                current_text = clean_text(parts[0]["text"])
            else:
                # 2️⃣ Otherwise, pick the last text entry in any 'data' array
                for part in reversed(parts):
                    data_array = part.get("data", [])
                    if isinstance(data_array, list) and data_array:
                        # Get only the last valid text in the data list
                        for data_item in reversed(data_array):
                            if (
                                data_item.get("kind") == "text"
                                and data_item.get("text", "").strip()
                            ):
                                current_text = clean_text(data_item["text"])
                                break
                        if current_text:
                            break

        print(f"🗣️ Extracted user text: {current_text!r}")

        if not current_text:
            return JSONResponse(
                {"status": "error", "message": "No valid user input text found."},
                status_code=400,
            )

        # --- Command handling ---
        if "history" in current_text.lower():
            history = get_history()
            response_text = (
                "\n".join(history) if history else "No fitness history found yet."
            )
        elif "refresh" in current_text.lower() or "force" in current_text.lower():
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            response_text = f"🔄 Refreshed Fitness Tip:\n{tip}"
        else:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_openai()
                add_tip_to_history(tip)
            response_text = f"💪 Today's Fitness Tip:\n{tip}"

        print(f"💬 Response: {response_text}")
        return JSONResponse(
            {
                "status": "success",
                "message": response_text,
            },
            status_code=200,
        )

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
        "version": "1.0.3",
        "status": "running",
        "message": "Telex Fitness Agent (REST, OpenAI) is active!",
    }
