import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required")

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
CACHE_FILE = os.getenv("CACHE_FILE", "cache.json")
HISTORY_SIZE = int(os.getenv("HISTORY_SIZE", "7"))
DAILY_TIP_HOUR_UTC = int(os.getenv("DAILY_TIP_HOUR_UTC", "7"))
MIN_OPENAI_CALL_INTERVAL = float(os.getenv("MIN_OPENAI_CALL_INTERVAL", "3"))  # seconds
MAX_TIP_LENGTH_CHARS = int(os.getenv("MAX_TIP_LENGTH_CHARS", "280"))
