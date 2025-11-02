from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


# -------------------------------------------------------------------
# 🎯 Message Parts
# -------------------------------------------------------------------
class TextPart(BaseModel):
    kind: Literal["text"]
    text: str


class FilePart(BaseModel):
    kind: Literal["file"]
    file_url: str


MessagePart = TextPart | FilePart


# -------------------------------------------------------------------
# 🗣️ Message Object
# -------------------------------------------------------------------
class Message(BaseModel):
    kind: Literal["message"]
    messageId: str
    role: str
    parts: list[MessagePart]
    taskId: str


# -------------------------------------------------------------------
# 🧩 Artifact Object
# -------------------------------------------------------------------
class Artifact(BaseModel):
    artifactId: str
    name: str
    parts: list[MessagePart]


# -------------------------------------------------------------------
# 🔄 Status Object
# -------------------------------------------------------------------
class Status(BaseModel):
    state: str
    timestamp: datetime
    message: Message


# -------------------------------------------------------------------
# 🧠 Result Object
# -------------------------------------------------------------------
class Result(BaseModel):
    id: str
    contextId: str
    status: Status
    artifacts: list[Artifact]
    history: list[Any]
    kind: Literal["task"]


# -------------------------------------------------------------------
# 📤 RPC Response
# -------------------------------------------------------------------
class RpcResponse(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    result: Result
