from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

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


@app.post("/message")
async def message(request: Request):
    """Accepts A2A Telex requests and returns fitness tips to the chatbox."""
    try:
        payload = await request.json()
        print("📩 Incoming payload:", payload)

        params = payload.get("params", {})
        message_obj = params.get("message", {})
        parts = message_obj.get("parts", [])
        config = params.get("configuration", {}).get("pushNotificationConfig", {})

        push_url = config.get("url")
        push_token = config.get("token")

        # --- Extract user text ---
        current_text = ""
        if parts:
            # First part should be Telex’s interpretation of user intent
            if parts[0].get("kind") == "text" and parts[0].get("text"):
                current_text = parts[0]["text"].strip()
            else:
                # fallback: maybe from the data array
                data_parts = parts[0].get("data", []) if len(parts) > 0 else []
                if data_parts:
                    current_text = data_parts[-1].get("text", "").strip()

        print(f"🗣️ Extracted text: {current_text}")

        if not current_text:
            return JSONResponse(
                {"status": "error", "message": "No valid user input text found."},
                status_code=400,
            )

        # --- Command handling ---
        if "history" in current_text.lower():
            history = get_history()
            response_text = "\n".join(history) if history else "No fitness history found yet."
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

        # --- Push message back to Telex chat ---
        if push_url and push_token:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {push_token}"}
                data = {
                    "kind": "message",
                    "role": "assistant",
                    "parts": [{"kind": "text", "text": response_text}],
                }
                await client.post(push_url, json=data, headers=headers)
                print("📤 Sent response to Telex chat UI.")

        return {"status": "ok", "message": "Response sent to Telex chat."}

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
        "version": "1.0.1",
        "status": "running",
        "message": "Telex Fitness Agent (REST, OpenAI) is active!",
    }
