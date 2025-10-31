from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tips import generate_tip

from cache import ensure_cache_exists, load_cache, save_tip
from scheduler import schedule_daily_job, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown lifecycle."""
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


app = FastAPI(title="Telex AI Fitness Agent (REST, OpenAI)", lifespan=lifespan)


@app.get("/manifest")
def manifest():
    """Metadata for Telex integration."""
    return {
        "name": "Fitness Tip Agent (OpenAI)",
        "version": "1.1.0",
        "author": "Wilson Icheku",
        "description": "An AI-powered health & fitness agent using OpenAI to generate daily wellness tips.",
        "endpoints": {
            "message": "/message",
            "manifest": "/manifest",
        },
        "actions": ["get_daily_tip", "get_history", "force_refresh"],
    }


@app.post("/message")
async def message(request: Request):
    """Main endpoint — accepts user input and returns AI-generated tips."""
    data = await request.json()
    user_input = data.get("text", "").lower().strip()

    if "history" in user_input:
        tips = load_cache()
        return {"status": "ok", "action": "get_history", "data": tips}

    if "refresh" in user_input or "force" in user_input:
        tip = await generate_tip(force_new=True)
        save_tip(tip)
        return {"status": "ok", "action": "force_refresh", "message": tip}

    tip = await generate_tip()
    save_tip(tip)
    return {"status": "ok", "action": "get_daily_tip", "message": tip}


@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Telex Fitness Agent (REST, OpenAI) is active!",
    }
