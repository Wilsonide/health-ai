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
        config = params.get("configuration", {}).get("pushNotificationConfig", {})

        push_url = config.get("url")
        push_token = config.get("token")

        current_text = ""

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

        # --- Push message back to Telex chat ---
        # --- Push message back to Telex chat ---
        if push_url and push_token:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {push_token}",
                    "Content-Type": "application/json",
                }

                # ✅ Correct Telex chat payload shape
                payload_to_telex = {
                    "kind": "message",
                    "role": "assistant",
                    "parts": [
                        {
                            "kind": "text",
                            "text": response_text,
                        },
                    ],
                }

                print(f"📡 Pushing to Telex: {push_url}")
                print(f"🔐 Using token: {push_token[:6]}...")

                try:
                    push_response = await client.post(
                        push_url, json=payload_to_telex, headers=headers, timeout=10.0
                    )

                    print(
                        f"📨 Push status: {push_response.status_code} - {push_response.text}"
                    )

                    if push_response.status_code >= 400:
                        return JSONResponse(
                            {
                                "status": "error",
                                "message": f"Telex push failed ({push_response.status_code})",
                                "response": push_response.text,
                            },
                            status_code=500,
                        )

                except Exception as push_err:
                    print(f"⚠️ Push error: {push_err}")
                    return JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to push message to Telex chat.",
                            "error": str(push_err),
                        },
                        status_code=500,
                    )

        else:
            print("⚠️ No push_url or push_token provided in payload.")
            return JSONResponse(
                {
                    "status": "error",
                    "message": "Missing push_url or push_token in configuration.",
                },
                status_code=400,
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
