import os
import random
import re

from openai import AsyncOpenAI

import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are a friendly, motivational AI health assistant. Generate a short, positive, and practical daily health or fitness tip.
Each tip should focus on one topic (fitness, nutrition, sleep, or mindfulness).
Avoid repeating previous tips, giving medical advice, or using emojis.
Keep it under 25 words.
"""


def sanitize_tip(tip: str) -> str:
    """Clean up unwanted characters, symbols, or overly long tips."""
    tip = tip.strip()
    tip = re.sub(r"[\r\n]+", " ", tip)
    tip = re.sub(r"[^a-zA-Z0-9.,'!? ]+", "", tip)
    if len(tip) > 120:
        tip = tip[:120].rsplit(" ", 1)[0] + "..."
    return tip


async def generate_tip() -> str:
    """Generate a clean, short AI tip using OpenAI."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Give me a daily health or fitness tip."},
            ],
            max_tokens=60,
            temperature=0.8,
        )
        tip = response.choices[0].message.content.strip()
        return sanitize_tip(tip)
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ OpenAI error: {e}")
        fallback_tips = [
            "Drink a glass of water first thing in the morning.",
            "Take a short walk to refresh your mind.",
            "Stretch your back and neck every hour while working.",
        ]
        return random.choice(fallback_tips)
