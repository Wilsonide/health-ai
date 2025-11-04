from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# 🎯 Message Parts
# -------------------------------------------------------------------
class TextPart(BaseModel):
    kind: Literal["text"]
    text: str


class FilePart(BaseModel):
    kind: Literal["file"]
    file_url: str


class DataPart(BaseModel):
    kind: Literal["data"]
    data: list[dict[str, Any]]


# ✅ Allow text, file, and data kinds
class MessagePart(BaseModel):
    kind: Literal["text", "data", "file"]
    text: str | None = None
    data: Any | None = None
    file_url: str | None = None


# -------------------------------------------------------------------
# 🗣️ Message Object
# -------------------------------------------------------------------
class Message(BaseModel):
    kind: Literal["message"] = "message"
    role: Literal["user", "agent", "system"]
    parts: list[MessagePart]
    messageId: str = Field(default_factory=lambda: str(uuid4()))
    taskId: str | None = None
    metadata: dict[str, Any] | None = None


# -------------------------------------------------------------------
# 🧩 Artifact Object
# -------------------------------------------------------------------
class Artifact(BaseModel):
    artifactId: str
    name: str
    parts: list[MessagePart]  # ✅ supports both text/file parts


# -------------------------------------------------------------------
# 🔄 Status Object
# -------------------------------------------------------------------
class Status(BaseModel):
    state: Literal["working", "completed", "input-required", "failed"]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    message: Message


# -------------------------------------------------------------------
# 🧠 Result Object
# -------------------------------------------------------------------
class Result(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    contextId: str = Field(default_factory=lambda: str(uuid4()))
    status: Status
    artifacts: list[Artifact] = []
    history: list[Message] | Any = []
    kind: Literal["task"] = "task"


# -------------------------------------------------------------------
# ❌ RPC Error Object
# -------------------------------------------------------------------
class RpcError(BaseModel):
    code: int
    message: str
    data: Any | None = None


# -------------------------------------------------------------------
# 📤 RPC Response
# -------------------------------------------------------------------
class RpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str
    result: Result | None = None
    error: dict[str, Any] | None = None


# -------------------------------------------------------------------
# ⚙️ Configuration Models
# -------------------------------------------------------------------
class AuthenticationConfig(BaseModel):
    schemes: list[str]


class PushNotificationConfig(BaseModel):
    url: str
    token: str
    authentication: AuthenticationConfig


class Configuration(BaseModel):
    acceptedOutputModes: list[str] | None = None
    historyLength: int | None = None
    pushNotificationConfig: PushNotificationConfig | None = None
    blocking: bool | None = None


class RpcRequestParams(BaseModel):
    message: Message
    configuration: Configuration | None = None


class MessageConfiguration(BaseModel):
    blocking: bool = True
    acceptedOutputModes: list[str] = ["text/plain", "image/png"]


class MessageParams(BaseModel):
    message: Message
    configuration: MessageConfiguration = Field(default_factory=MessageConfiguration)


class ExecuteParams(BaseModel):
    contextId: str | None = None
    taskId: str | None = None
    messages: list[Message]


class RpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send", "execute"]
    params: MessageParams | ExecuteParams


class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send", "execute"]
    params: MessageParams | ExecuteParams
