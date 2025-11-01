from pydantic import BaseModel


class MessageDataItem(BaseModel):
    kind: str
    text: str | None = None


class MessagePart(BaseModel):
    kind: str
    text: str | None = None  # For "text" parts
    data: list[MessageDataItem] | None = None  # For "data" parts


class Message(BaseModel):
    kind: str
    role: str
    parts: list[MessagePart]
    messageId: str | None = None


class Params(BaseModel):
    message: Message


class TelexRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Params
