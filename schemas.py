from pydantic import BaseModel


class MessageDataItem(BaseModel):
    kind: str
    text: str | None = None


class MessagePart(BaseModel):
    kind: str
    text: str | None = None  # ✅ optional now
    data: list[MessageDataItem] | None = None  # ✅ supports data parts too


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
