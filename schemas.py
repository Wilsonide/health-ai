from typing import Any

from pydantic import BaseModel


class MessagePart(BaseModel):
    kind: str
    text: str | None = None
    data: list[Any] | None = None


class MessageParams(BaseModel):
    kind: str
    role: str
    parts: list[MessagePart]
    messageId: str | None = None


class TelexParams(BaseModel):
    message: MessageParams


class TelexRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: TelexParams
