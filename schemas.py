from pydantic import BaseModel, field_validator

from utils import sanitize_text


class DailyTip(BaseModel):
    tip: str

    @field_validator("tip", mode="before")
    def clean_and_validate(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Tip must be a non-empty string")
        cleaned = sanitize_text(v)
        if len(cleaned) < 5:
            raise ValueError("Tip too short after sanitization")
        # simple domain keyword check
        keywords = [
            "health",
            "fitness",
            "exercise",
            "sleep",
            "water",
            "hydrate",
            "stretch",
            "move",
            "diet",
            "walk",
        ]
        if not any(k in cleaned.lower() for k in keywords):
            # still allow some short actionable tips containing verbs like 'walk' or 'drink'
            raise ValueError("Tip doesn't appear to be health/fitness-related")
        # enforce length cap (optional)
        return cleaned


class RpcRequest(BaseModel):
    jsonrpc: str
    id: int | str | None = None
    method: str
    params: dict = {}


class RpcError(BaseModel):
    code: int
    message: str
    data: dict | None = None


class RpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str | None
    result: dict | None = None
    error: RpcError | None = None
