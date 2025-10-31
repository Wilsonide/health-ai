import datetime
import json
from pathlib import Path

from config import CACHE_FILE, HISTORY_SIZE

_cache_path = Path(CACHE_FILE)


def _read_file():
    try:
        with _cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"history": []}
    except json.JSONDecodeError:
        return {"history": []}


def _write_file(data):
    with _cache_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_history():
    data = _read_file()
    return data.get("history", [])


def get_cached_tip_for_today():
    history = get_history()
    if history:
        last = history[-1]
        if last.get("date") == datetime.date.today().isoformat():  # noqa: DTZ011
            return last.get("tip")
    return None


def add_tip_to_history(tip: str):
    data = _read_file()
    history = data.get("history", [])
    entry = {"date": datetime.date.today().isoformat(), "tip": tip}  # noqa: DTZ011
    history.append(entry)
    # keep last N
    history = history[-HISTORY_SIZE:]
    data["history"] = history
    _write_file(data)
    return entry


def ensure_cache_exists():
    if not _cache_path.exists():
        _write_file({"history": []})
