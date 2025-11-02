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


MessagePart = TextPart


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
    parts: list[FilePart | TextPart]


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


class AuthenticationConfig(BaseModel):
    schemes: list[str]


class PushNotificationConfig(BaseModel):
    url: str
    token: str
    authentication: AuthenticationConfig


class Configuration(BaseModel):
    acceptedOutputModes: list[str]  # noqa: N815
    historyLength: int  # noqa: N815
    pushNotificationConfig: PushNotificationConfig  # noqa: N815
    blocking: bool


class RpcRequestParams(BaseModel):
    message: Message
    configuration: Configuration | None = None


class RpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: Literal["message/send"]
    params: RpcRequestParams


# -------------------------------------------------------------------
# ❌ RPC Error Object
# -------------------------------------------------------------------
class RpcError(BaseModel):
    code: int
    message: str
    data: Any | None = None
