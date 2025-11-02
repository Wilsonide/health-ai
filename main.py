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
    """Accepts Telex A2A JSON-RPC requests and returns fitness tips."""
    try:
        data = await request.json()
        print("📩 Incoming payload:", data)

        # ✅ Validate incoming RPC request
        rpc_request = RpcRequest(**data)

        # Verify request format
        if rpc_request.jsonrpc != "2.0" or rpc_request.method != "message/send":
            error = RpcError(code=-32600, message="Invalid JSON-RPC request format")
            return JSONResponse(
                content=RpcResponse(
                    jsonrpc="2.0",
                    id=rpc_request.id,
                    error=error,
                ).model_dump(mode="json"),
                status_code=400,
            )

        params = rpc_request.params
        message_obj = params.message
        parts = message_obj.parts or []

        # --- Extract last valid user text ---
        current_text = ""
        for part in reversed(parts):
            if part.kind == "text" and part.text.strip():
                current_text = clean_text(part.text)
                break
            if part.kind == "data":
                for item in reversed(part.data):
                    if item.kind == "text" and item.text.strip():
                        current_text = clean_text(item.text)
                        break
            if current_text:
                break

        print(f"🗣️ Extracted user text: {current_text!r}")

        if not current_text:
            error = RpcError(code=-32602, message="No valid user input text found.")
            return JSONResponse(
                content=RpcResponse(
                    jsonrpc="2.0", id=rpc_request.id, error=error
                ).model_dump(mode="json"),
                status_code=400,
            )

        # --- Command Handling ---
        if "history" in current_text.lower() or "log" in current_text.lower():
            history = get_history()
            response_text = (
                "No fitness history found yet."
                if not history
                else "📜 Your Fitness Tip History:\n"
                + "\n".join(
                    item.get("tip") if isinstance(item, dict) else str(item)
                    for item in history
                )
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

        print(f"💬 Response text: {response_text}")

        # --- ✅ Construct A2A-Compliant RpcResult ---
        msg_part = MessageResponsePart(kind="text", text=response_text)
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

        print("✅ Outgoing RPC response:", rpc_response.model_dump())
        return JSONResponse(
            content=rpc_response.model_dump(mode="json"), status_code=200
        )

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        error = RpcError(
            code=-32000, message="Internal Server Error", data={"detail": str(e)}
        )
        rpc_response = RpcResponse(jsonrpc="2.0", id=None, error=error)
        return JSONResponse(
            content=rpc_response.model_dump(mode="json"), status_code=500
        )


@app.get("/")
def root():
    return {
        "name": "Telex AI Fitness Tip Agent",
        "short_description": "Provides daily fitness tips, retrieves history logs, and refreshes tips.",
        "description": (
            "An A2A agent that generates AI-powered daily fitness tips, "
            "retrieves fitness history, and supports tip refreshing via JSON-RPC 2.0."
        ),
        "author": "Wilson Icheku",
        "version": "1.0.5",
        "status": "running",
        "message": "Telex Fitness Agent (A2A, OpenAI) is active!",
    }
