import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cache import (
    add_tip_to_history,
    ensure_cache_exists,
    get_cached_tip_for_today,
    get_history,
)
from openai_client import generate_tip_from_gemini
from scheduler import schedule_daily_job, scheduler
from schemas import (
    MessageResponse,
    MessageResponsePart,
    ResponseStatus,
    RpcError,
    RpcRequest,
    RpcResponse,
    RpcResult,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: start cache + scheduler."""
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


app = FastAPI(
    title="Telex AI Fitness Tip Agent",
    lifespan=lifespan,
    description=(
        "An A2A agent that provides AI-powered daily fitness and wellness tips. "
        "It supports fetching today's cached tip, refreshing for a new one, "
        "and viewing a full history of past tips."
    ),
)

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean_text(text: str) -> str:
    """Remove HTML tags and trim whitespace."""
    return re.sub(r"<.*?>", "", text or "").strip()


@app.post("/message")
async def message(request: Request):
    """Handles Telex A2A message/send requests."""
    try:
        data = await request.json()
        print("📩 Incoming payload:", data)

        # ✅ Validate JSON-RPC structure
        rpc_request = RpcRequest(**data)
        if rpc_request.jsonrpc != "2.0" or rpc_request.method != "message/send":
            error = RpcError(code=-32600, message="Invalid JSON-RPC request format")
            return JSONResponse(
                RpcResponse(jsonrpc="2.0", id=rpc_request.id, error=error).model_dump(),
                status_code=400,
            )

        params = rpc_request.params
        message_obj = params.message
        parts = message_obj.parts or []

        # --- Extract last valid user text ---
        user_text = ""
        for part in reversed(parts):
            if part.kind == "text" and part.text.strip():
                user_text = clean_text(part.text)
                break
            if part.kind == "data":
                for item in reversed(part.data):
                    if item.kind == "text" and item.text.strip():
                        user_text = clean_text(item.text)
                        break
            if user_text:
                break

        print(f"🗣️ User input: {user_text!r}")

        if not user_text:
            error = RpcError(
                code=-32602, message="No valid text input found in message."
            )
            return JSONResponse(
                RpcResponse(jsonrpc="2.0", id=rpc_request.id, error=error).model_dump(),
                status_code=400,
            )

        # --- Command Logic ---
        if "history" in user_text.lower() or "log" in user_text.lower():
            history = get_history()
            if not history:
                tip_text = "No fitness history found yet."
            else:
                tip_text = "📜 Your Fitness Tip History:\n" + "\n".join(
                    item.get("tip") if isinstance(item, dict) else str(item)
                    for item in history
                )

        elif "refresh" in user_text.lower() or "new tip" in user_text.lower():
            tip = await generate_tip_from_gemini()
            add_tip_to_history(tip)
            tip_text = f"🔄 New Fitness Tip:\n{tip}"

        else:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_gemini()
                add_tip_to_history(tip)
            tip_text = f"💪 Today's Fitness Tip:\n{tip}"

        print(f"💬 Response message: {tip_text}")

        # --- ✅ Construct RpcResult ---
        msg_part = MessageResponsePart(kind="text", text=tip_text)
        msg_response = MessageResponse(kind="message", role="agent", parts=[msg_part])

        rpc_result = RpcResult(
            id=str(uuid.uuid4()),
            contextId=str(rpc_request.id or uuid.uuid4()),
            kind="task",
            status=ResponseStatus(
                state="completed",
                timestamp=datetime.now(UTC).isoformat(),
                message=msg_response,
            ),
            artifacts=[],
        )

        rpc_response = RpcResponse(
            jsonrpc="2.0",
            id=rpc_request.id,
            result=rpc_result,
        )

        print("✅ Sending RPC Response:", rpc_response.model_dump())
        return JSONResponse(content=rpc_response.model_dump(), status_code=200)

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        error = RpcError(
            code=-32000, message="Internal Server Error", data={"detail": str(e)}
        )
        return JSONResponse(
            RpcResponse(jsonrpc="2.0", id=None, error=error).model_dump(),
            status_code=500,
        )


@app.get("/")
def root():
    """Expose metadata for discovery."""
    return {
        "id": "fitAI_agent_001",
        "name": "fitness_tip_agent",
        "category": "health & wellness",
        "short_description": "Provides daily AI-powered fitness tips with refresh and history retrieval.",
        "long_description": (
            "An intelligent fitness and health assistant that delivers daily, personalized "
            "AI-generated tips on exercise, nutrition, and wellness. "
            "You can:\n"
            "- 💪 Get today’s cached daily fitness tip\n"
            "- 🔄 Manually refresh for a brand new tip\n"
            "- 📜 View your complete history of past tips\n\n"
            "Perfect for keeping your wellness journey consistent and motivated every day."
        ),
        "author": "Wilson Icheku",
        "version": "1.1.1",
        "status": "running",
        "message": "Telex AI Fitness Tip Agent active — ready for daily tips, refresh, and history logs!",
    }
