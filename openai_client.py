import asyncio
import time

from fastapi import HTTPException
from openai import OpenAI
from utils import sanitize_text

from config import (
    MAX_TIP_LENGTH_CHARS,
    MIN_OPENAI_CALL_INTERVAL,
    MODEL_NAME,
    OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY)
_last_call_ts = 0.0


async def _rate_guard():
    global _last_call_ts  # noqa: PLW0603
    now = time.time()
    delta = now - _last_call_ts
    if delta < MIN_OPENAI_CALL_INTERVAL:
        await asyncio.sleep(MIN_OPENAI_CALL_INTERVAL - delta)
    _last_call_ts = time.time()


async def generate_tip_from_openai() -> str:
    """
    Calls OpenAI to get a raw tip string, sanitizes & validates it via Pydantic.
    Returns validated tip text.
    """  # noqa: D205
    await _rate_guard()

    system_msg = {
        "role": "system",
        "content": (
            "You are a concise, friendly daily health & fitness coach. "
            "Produce one short actionable tip (1-2 sentences) aimed at general adults. "
            "Keep it safe and non-medical."
        ),
    }
    user_msg = {
        "role": "user",
        "content": "Give one short daily health and fitness tip for adults, under 200 characters.",
    }

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[system_msg, user_msg],
            max_tokens=120,
            temperature=0.7,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"OpenAI error: {exc}")  # noqa: B904

    try:
        raw = resp.choices[0].message.content
        # sanitize lightly before validation
        raw = sanitize_text(raw)
        # validate with Pydantic; this will raise if invalid
        validated = raw
        # enforce max char length
        tip_out = validated
        if len(tip_out) > MAX_TIP_LENGTH_CHARS:
            tip_out = tip_out[:MAX_TIP_LENGTH_CHARS].rsplit(" ", 1)[0] + "..."
        else:
            return tip_out
    except Exception as e:  # noqa: BLE001
        # Convert validation/openai parse errors to HTTPException for upstream handling
        raise HTTPException(status_code=502, detail=f"Tip validation failed: {e}")  # noqa: B904
