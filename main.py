from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from cache import ensure_cache_exists
from rpc import handle_rpc
from scheduler import schedule_daily_job, scheduler  # 👈 import scheduler instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown lifecycle:
    - Ensures cache file exists
    - Starts the scheduler
    - Stops it gracefully on shutdown.
    """  # noqa: D205
    # ---- Startup ----
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")

    # Run the application
    yield

    # ---- Shutdown ----
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


# --- FastAPI app instance ---
app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)


# --- JSON-RPC Endpoint ---
@app.post("/rpc")
async def rpc_endpoint(request: Request):
    """
    Single JSON-RPC 2.0 endpoint.
    Accepts a JSON-RPC request body and returns a JSON-RPC response.
    """  # noqa: D205
    return await handle_rpc(request)


# --- Root status endpoint (optional) ---
@app.get("/")
def root():
    return {
        "status": "Telex AI Fitness Tip Agent running",
        "rpc_endpoint": "POST /rpc",
    }


@app.get("/manifest")
def manifest():
    """
    Returns metadata about this A2A agent for Telex integration.
    Required fields: name, short_description, description, author, version.
    """  # noqa: D205
    return {
        "name": "Telex AI Fitness Tip Agent",
        "short_description": "Provides daily fitness tips via A2A JSON-RPC protocol.",
        "description": (
            "An A2A agent that generates and sends AI-powered daily fitness "
            "tips using JSON-RPC 2.0. Designed for use with Telex workflows."
        ),
        "author": "Wilson Icheku",
        "version": "1.0.0",
    }
