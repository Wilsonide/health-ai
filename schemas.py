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


class DataPart(BaseModel):
    kind: Literal["data"]
    data: list[dict[str, Any]]


# ✅ Allow text, file, and data kinds
MessagePart = TextPart | FilePart | DataPart


# -------------------------------------------------------------------
# 🗣️ Message Object
# -------------------------------------------------------------------
class Message(BaseModel):
    kind: Literal["message"]
    messageId: str
    role: str
    parts: list[MessagePart]
    taskId: str | None = None  # ✅ some messages won't have it


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
    history: list[Any] = []  # ✅ safe default
    kind: Literal["task"]


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
    jsonrpc: Literal["2.0"]
    id: str | None = None  # ✅ allow None in error cases
    result: Result | None = None  # ✅ optional for error
    error: RpcError | None = None  # ✅ properly support JSON-RPC error


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
    acceptedOutputModes: list[str]
    historyLength: int
    pushNotificationConfig: PushNotificationConfig
    blocking: bool


class RpcRequestParams(BaseModel):
    message: Message
    configuration: Configuration | None = None


class RpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: Literal["message/send"]
    params: RpcRequestParams
