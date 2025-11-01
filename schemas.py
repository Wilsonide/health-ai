from typing import Any
from pydantic import BaseModel


class TelexMessagePart(BaseModel):
    kind: str
    text: str


class TelexMessage(BaseModel):
    kind: str
    role: str
    parts: list[TelexMessagePart]
    messageId: str


class TelexParams(BaseModel):
    message: TelexMessage
    configuration: dict[str, Any]


class TelexRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: TelexParams
