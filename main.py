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
from openai_client import get_gemini_reply
from scheduler import schedule_daily_job, scheduler
from schemas import (
    Artifact,
    Message,
    MessagePart,
    Result,
    RpcRequest,
    RpcResponse,
    Status,
    TextPart,
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
            return JSONResponse(
                RpcResponse(jsonrpc="2.0", id=rpc_request.id).model_dump(mode="json"),
                status_code=200,
            )

        params = rpc_request.params
        message_obj = params.message
        parts = message_obj.parts or []

        print(f"📝 Messageparams : {message_obj}")

        # --- Extract last valid user text ---
        user_text = ""
        tip_text = ""

        for part in reversed(parts):
            kind = (
                part.get("kind")
                if isinstance(part, dict)
                else getattr(part, "kind", None)
            )

            if kind == "text":
                text_value = (
                    part.get("text")
                    if isinstance(part, dict)
                    else getattr(part, "text", "")
                )
                if text_value and text_value.strip():
                    user_text = clean_text(text_value)
                    break

            elif kind == "data":
                data_items = (
                    part.get("data")
                    if isinstance(part, dict)
                    else getattr(part, "data", [])
                )
                for item in reversed(data_items):
                    item_kind = (
                        item.get("kind")
                        if isinstance(item, dict)
                        else getattr(item, "kind", None)
                    )
                    item_text = (
                        item.get("text")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    if item_kind == "text" and item_text and item_text.strip():
                        user_text = clean_text(item_text)
                        break

            if user_text:
                break

        print(f"🗣️ User input: {user_text!r}")

        if not user_text:
            return JSONResponse(
                RpcResponse(jsonrpc="2.0", id=rpc_request.id).model_dump(mode="json"),
                status_code=200,
            )

        # --- Command Logic ---
        if "history" in user_text.lower() or "log" in user_text.lower():
            history = get_history()
            if not history:
                tip_text = "No fitness history found yet."
            else:
                tip_text = "\n".join(
                    item.get("tip") if isinstance(item, dict) else str(item)
                    for item in history
                )

            """ elif "refresh" in user_text.lower() or "new tip" in user_text.lower():
            tip = await get_gemini_reply(
                user_id=rpc_request.id,
                user_message=user_text,
            )
            add_tip_to_history(tip)
            tip_text = f"{tip}" """

        else:
            tip = await get_gemini_reply(user_id=rpc_request.id, user_message=user_text)
            tip_text = f"{tip}"

        print(f"💬 Response message: {tip_text}")

        # --- ✅ Construct RpcResult ---
        msg_part = MessagePart(kind="text", text=tip_text, data=None, file_url=None)
        msg_response = Message(
            kind="message",
            role="agent",
            parts=[msg_part],
            taskId=str(uuid.uuid4()),
            messageId=str(uuid.uuid4()),
            metadata=None,
        )

        artifacts = [
            Artifact(
                artifactId=str(uuid.uuid4()),
                name="health_response",
                parts=[
                    MessagePart(
                        kind="text",
                        text=tip_text,  # SAME text as in message
                        data=None,
                        file_url=None,
                    ),
                ],
            ),
        ]

        rpc_result = Result(
            id=str(uuid.uuid4()),
            contextId=str(uuid.uuid4()),
            status=Status(
                state="completed",
                timestamp=datetime.utcnow().isoformat() + "Z",
                message=msg_response,
            ),
            artifacts=artifacts,
            history=parts,
            kind="task",
        )

        rpc_response = RpcResponse(
            id=rpc_request.id,
            result=rpc_result,
        )

        print("✅ Sending RPC Response:", rpc_response.model_dump())
        return JSONResponse(
            content=rpc_response.model_dump(mode="json"),
            status_code=200,
        )

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        return JSONResponse(
            RpcResponse(jsonrpc="2.0", id=rpc_request.id).model_dump(mode="json"),
            status_code=200,
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
