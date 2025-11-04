import asyncio
import time

import google.generativeai as genai
from fastapi import HTTPException

from config import GEMINI_API_KEY, MIN_OPENAI_CALL_INTERVAL, MODEL_NAME
from utils import sanitize_text

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
_last_call_ts = 0.0

# In-memory user session store
_user_sessions = {}


async def _rate_guard():
    """Prevent hitting Gemini rate limits."""
    global _last_call_ts
    now = time.time()
    delta = now - _last_call_ts
    if delta < MIN_OPENAI_CALL_INTERVAL:
        await asyncio.sleep(MIN_OPENAI_CALL_INTERVAL - delta)
    _last_call_ts = time.time()


def get_or_create_session(user_id: str):
    """Return or initialize Gemini chat session for the user."""
    if user_id in _user_sessions:
        return _user_sessions[user_id]["session"]

    model = genai.GenerativeModel(MODEL_NAME)
    chat_session = model.start_chat(history=[])
    _user_sessions[user_id] = {"history": [], "session": chat_session}
    return chat_session


def add_to_history(user_id: str, role: str, message: str):
    """Add message to in-memory chat history."""
    if user_id not in _user_sessions:
        get_or_create_session(user_id)

    _user_sessions[user_id]["history"].append(
        {"role": role, "parts": [{"text": message}]}
    )
    _user_sessions[user_id]["history"] = _user_sessions[user_id]["history"][-10:]


def get_history(user_id: str):
    """Retrieve chat history for the user."""
    return _user_sessions.get(user_id, {}).get("history", [])


async def get_gemini_reply(user_id: str, user_message: str) -> str:
    """
    Generate Gemini 2.5 Flash reply focused strictly on body/health topics.
    - Responds warmly to greetings.
    - Declines unrelated topics.
    - Maintains per-user chat memory.
    - Retries on timeout and returns friendly fallback on failure.
    """
    await _rate_guard()

    chat_session = get_or_create_session(user_id)
    add_to_history(user_id, "user", user_message)

    lower_msg = user_message.lower().strip()

    # --- Greetings handler ---
    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good evening",
        "good afternoon",
        "yo",
        "sup",
        "what's up",
    ]
    if any(greet in lower_msg for greet in greetings):
        greeting_reply = (
            "Hey there! 👋 I’m FitAI, your personal health and fitness buddy. "
            "Ask me about workouts, nutrition, or wellness to get started!"
        )
        add_to_history(user_id, "model", greeting_reply)
        return greeting_reply

    # --- Health keywords filter ---
    health_keywords = [
        "health",
        "body",
        "fitness",
        "workout",
        "exercise",
        "diet",
        "nutrition",
        "stretch",
        "sleep",
        "hydration",
        "wellness",
        "training",
        "muscle",
        "posture",
        "yoga",
        "cardio",
        "running",
        "strength",
        "mental health",
    ]
    if not any(k in lower_msg for k in health_keywords):
        polite_refusal = (
            "I'm FitAI 💪 — I only share tips and guidance about health, fitness, and body wellness. "
            "Try asking me about workouts, diet, or posture!"
        )
        add_to_history(user_id, "model", polite_refusal)
        return polite_refusal

    # --- Health response mode ---
    prompt = (
        "You are FitAI, a concise, friendly health and fitness expert. "
        "Only give responses related to physical health, workouts, nutrition, recovery, or wellness. "
        "Stay positive, practical, and under 200 characters.\n\n"
        f"User said: {user_message}\n\n"
        "Your response:"
    )

    # --- Retry logic with fallback ---
    for attempt in range(2):  # one retry allowed
        try:
            await _rate_guard()
            start = time.time()
            response = await asyncio.wait_for(
                asyncio.to_thread(chat_session.send_message, prompt),
                timeout=25.0,  # longer timeout
            )
            print(f"✅ Gemini responded in {time.time() - start:.1f}s")
            break  # success
        except asyncio.TimeoutError:
            print(f"⚠️ Gemini timeout on attempt {attempt + 1}")
            if attempt == 0:
                # retry with a fresh session
                _user_sessions.pop(user_id, None)
                chat_session = get_or_create_session(user_id)
                continue
            # fallback after retry
            fallback = (
                "Sorry, FitAI’s connection is a bit slow right now. "
                "Please try again in a few seconds 💪."
            )
            add_to_history(user_id, "model", fallback)
            return fallback
        except Exception as exc:
            print(f"❌ Gemini error: {exc}")
            fallback = (
                "Oops! Something went wrong while fetching your health tip. "
                "Please try again shortly 💚."
            )
            add_to_history(user_id, "model", fallback)
            return fallback

    # --- Extract Gemini text ---
    raw = getattr(response, "text", "")
    if not raw and getattr(response, "candidates", None):
        raw = response.candidates[0].content.parts[0].text

    clean = sanitize_text(raw or "").strip()
    if not clean:
        fallback = (
            "Hmm, I couldn’t get a response just now — please try again in a bit 💪."
        )
        add_to_history(user_id, "model", fallback)
        return fallback

    # Keep it concise
    if len(clean) > 200:
        clean = clean[:200].rsplit(" ", 1)[0] + "..."

    add_to_history(user_id, "model", clean)
    return clean


def get_user_chat_history(user_id: str):
    """Return stored chat history."""
    return get_history(user_id)
