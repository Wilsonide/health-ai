import asyncio
import time
from fastapi import HTTPException
from utils import sanitize_text
import google.generativeai as genai

from config import (
    MAX_TIP_LENGTH_CHARS,
    MIN_OPENAI_CALL_INTERVAL,
    GEMINI_API_KEY,
    MODEL_NAME,  # e.g. "gemini-1.5-flash"
)

genai.configure(api_key=GEMINI_API_KEY)
_last_call_ts = 0.0


async def _rate_guard():
    """Ensure we don’t exceed Gemini rate limits."""
    global _last_call_ts
    now = time.time()
    delta = now - _last_call_ts
    if delta < MIN_OPENAI_CALL_INTERVAL:
        await asyncio.sleep(MIN_OPENAI_CALL_INTERVAL - delta)
    _last_call_ts = time.time()


async def generate_tip_from_gemini() -> str:
    """Get one short daily fitness tip via Gemini (with timeout & async safety)."""
    await _rate_guard()

    prompt = (
        "You are a concise, friendly daily health & fitness coach. "
        "Give one short, motivational, actionable health or fitness tip for adults. "
        "Keep it under 200 characters and positive."
    )

    model = genai.GenerativeModel(MODEL_NAME)

    try:
        # Run Gemini in a background thread with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=8.0,  # seconds
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Gemini request timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini error: {exc}")

    try:
        # Extract and sanitize text
        raw = getattr(response, "text", "")
        if not raw and getattr(response, "candidates", None):
            raw = response.candidates[0].content.parts[0].text

        raw = sanitize_text(raw or "").strip()

        # Enforce character limit
        if len(raw) > MAX_TIP_LENGTH_CHARS:
            raw = raw[:MAX_TIP_LENGTH_CHARS].rsplit(" ", 1)[0] + "..."

        if not raw:
            raise ValueError("Gemini returned empty text")

        return raw

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tip processing failed: {e}")
