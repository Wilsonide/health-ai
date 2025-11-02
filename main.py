import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cache import (
    add_tip_to_history,
    ensure_cache_exists,
    get_cached_tip_for_today,
    get_history,
)
from openai_client import generate_tip_from_openai
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
    """Handle startup and shutdown lifecycle."""
    ensure_cache_exists()
    schedule_daily_job()
    print("✅ Scheduler started")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler stopped cleanly")


app = FastAPI(title="Telex AI Fitness Tip Agent", lifespan=lifespan)

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean_text(text: str) -> str:
    """Remove HTML tags and trim whitespace."""
    return re.sub(r"<.*?>", "", text or "").strip()


@app.post("/message")
async def message(request: Request):
    """Accepts Telex A2A JSON-RPC requests and returns fitness tips."""
    try:
        data = await request.json()
        print("📩 Incoming payload:", data)

        rpc_request = RpcRequest(**data)

        # Validate base A2A structure
        if rpc_request.jsonrpc != "2.0" or rpc_request.method != "message/send":
            error = RpcError(code=-32600, message="Invalid JSON-RPC request format")
            return JSONResponse(
                content=RpcResponse(
                    jsonrpc="2.0",
                    id=rpc_request.id,
                    error=error,
                ).model_dump(),
                status_code=400,
            )

        params = rpc_request.params
        message_obj = params.message
        parts = message_obj.parts

        current_text = ""

        # --- Extract user text ---
        if parts:
            for part in reversed(parts):
                if part.kind == "text" and part.text.strip():
                    current_text = clean_text(part.text)
                    break
                if hasattr(part, "data"):
                    for data_item in reversed(part.data):
                        if data_item.kind == "text" and data_item.text.strip():
                            current_text = clean_text(data_item.text)
                            break
                    if current_text:
                        break

        print(f"🗣️ Extracted user text: {current_text!r}")

        if not current_text:
            error = RpcError(code=-32602, message="No valid user input text found.")
            return JSONResponse(
                content=RpcResponse(
                    jsonrpc="2.0",
                    id=rpc_request.id,
                    error=error,
                ).model_dump(),
                status_code=400,
            )

        # --- Command handling ---
        if "history" in current_text.lower() or "log" in current_text.lower():
            history = get_history()
            if not history:
                response_text = "No fitness history found yet."
            else:
                safe_history = [
                    str(item.get("tip") if isinstance(item, dict) else item)
                    for item in history
                ]
                response_text = "📜 Your Fitness Tip History:\n" + "\n".join(
                    safe_history,
                )

        elif "refresh" in current_text.lower() or "force" in current_text.lower():
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            response_text = f"🔄 Refreshed Fitness Tip:\n{tip}"

        else:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_openai()
                add_tip_to_history(tip)
            response_text = f"💪 Today's Fitness Tip:\n{tip}"

        print(f"💬 Response: {response_text}")

        # --- ✅ Build proper A2A-compliant response ---
        msg_part = MessageResponsePart(kind="text", text=response_text)
        msg_response = MessageResponse(kind="message", role="agent", parts=[msg_part])

        rpc_result = RpcResult(
            id=str(uuid.uuid4()),
            contextId=str(rpc_request.id or uuid.uuid4()),
            status=ResponseStatus(
                state="completed",
                timestamp=datetime.now(UTC).isoformat(),
                message=msg_response,
            ),
            artifacts=[],
            kind="task",
        )

        rpc_response = RpcResponse(
            jsonrpc="2.0",
            id=rpc_request.id,
            result=rpc_result,
        )

        return JSONResponse(content=rpc_response.model_dump(), status_code=200)

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        error = RpcError(
            code=-32000, message="Internal Server Error", data={"detail": str(e)}
        )
        rpc_response = RpcResponse(jsonrpc="2.0", id=None, error=error)
        return JSONResponse(content=rpc_response.model_dump(), status_code=500)


@app.get("/")
def root():
    return {
        "name": "Telex AI Fitness Tip Agent",
        "short_description": "Provides daily fitness tips, retrieves full fitness history logs and allows refreshing tips.",
        "description": (
            "An A2A agent that generates and sends AI-powered daily fitness "
            "tips, retrieves full fitness history logs, and allows refreshing tips "
            "using JSON-RPC 2.0 — fully compliant with the Telex A2A standard."
        ),
        "author": "Wilson Icheku",
        "version": "1.1.0",
        "status": "running",
        "message": "Telex Fitness Agent (A2A, OpenAI) is active!",
    }
