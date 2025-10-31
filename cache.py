import json
from pathlib import Path

CACHE_FILE = Path("tips_cache.json")


def ensure_cache_exists():
    if not CACHE_FILE.exists():
        CACHE_FILE.write_text(json.dumps([]))


def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:  # noqa: BLE001
        return []


def save_tip(tip: str):
    tips = load_cache()
    tips.append(tip)
    CACHE_FILE.write_text(json.dumps(tips[-10:], indent=2))  # keep latest 10
