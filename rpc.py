from fastapi import Request
from fastapi.responses import JSONResponse

from cache import add_tip_to_history, get_cached_tip_for_today, get_history
from openai_client import generate_tip_from_openai
from schemas import RpcError, RpcRequest, RpcResponse


def build_rpc_response(
    result: dict | None, id_: int | str | None, error: RpcError | None = None
):
    """Helper to return a validated RpcResponse object as JSON."""
    response = RpcResponse(
        id=id_,
        result=result,
        error=error,
    )
    return JSONResponse(response.model_dump())


def rpc_error(id_, code, message, data=None):
    """Helper for building structured JSON-RPC error responses."""
    err = RpcError(code=code, message=message, data=data)
    return build_rpc_response(result=None, id_=id_, error=err)


async def handle_rpc(request: Request):  # noqa: C901, PLR0911
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return rpc_error(None, -32700, "Parse error: invalid JSON")

    try:
        req = RpcRequest(**body)
    except Exception as e:  # noqa: BLE001
        id_ = body.get("id") if isinstance(body, dict) else None
        return rpc_error(id_, -32600, f"Invalid Request: {e}")

    rpc_id = req.id
    method = req.method

    # Reject user parameters (agent doesn’t accept them)
    if req.params:
        return rpc_error(
            rpc_id, -32602, "This agent does not accept params in methods."
        )

    # ---- Methods ----
    if method == "get_daily_tip":
        try:
            tip = get_cached_tip_for_today()
            if not tip:
                tip = await generate_tip_from_openai()
                add_tip_to_history(tip)
            return build_rpc_response({"tip": tip}, rpc_id)
        except Exception as e:  # noqa: BLE001
            return rpc_error(rpc_id, -32000, f"Failed to get/generate tip: {e}")

    elif method == "get_history":
        try:
            history = get_history()
            return build_rpc_response({"history": history}, rpc_id)
        except Exception as e:  # noqa: BLE001
            return rpc_error(rpc_id, -32000, f"Failed to read history: {e}")

    elif method == "force_refresh":
        try:
            tip = await generate_tip_from_openai()
            add_tip_to_history(tip)
            return build_rpc_response({"tip": tip}, rpc_id)
        except Exception as e:  # noqa: BLE001
            return rpc_error(rpc_id, -32000, f"Failed to refresh tip: {e}")

    # Method not found
    return rpc_error(rpc_id, -32601, "Method not found")
