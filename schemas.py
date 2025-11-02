from typing import Any, Literal

from pydantic import BaseModel


# -------------------------------------------------------------------
# 📦 Message Parts
# -------------------------------------------------------------------
class TextPart(BaseModel):
    kind: Literal["text"]
    text: str


class DataItem(BaseModel):
    kind: Literal["text"]
    text: str


class DataPart(BaseModel):
    kind: Literal["data"]
    data: list[DataItem]


MessagePart = TextPart | DataPart


# -------------------------------------------------------------------
# 🗣️ Message Object
# -------------------------------------------------------------------
class Message(BaseModel):
    kind: Literal["message"]
    role: str
    parts: list[MessagePart]
    messageId: str | None = None


# -------------------------------------------------------------------
# ⚙️ Configuration Object
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# 📨 RPC Request (Telex A2A Standard)
# -------------------------------------------------------------------
class RpcRequestParams(BaseModel):
    message: Message
    configuration: Configuration | None = None


class RpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    method: Literal["message/send"]
    params: RpcRequestParams


# -------------------------------------------------------------------
# ❌ RPC Error Object
# -------------------------------------------------------------------
class RpcError(BaseModel):
    code: int
    message: str
    data: Any | None = None


# -------------------------------------------------------------------
# ✅ RPC Response (Telex A2A Standard)
# -------------------------------------------------------------------
class MessageResponsePart(BaseModel):
    kind: Literal["text"]
    text: str


class MessageResponse(BaseModel):
    kind: Literal["message"]
    role: Literal["agent"]
    parts: list[MessageResponsePart]
    messageId: str | None = None


class ResponseStatus(BaseModel):
    state: Literal["completed"]
    timestamp: str
    message: MessageResponse


class ArtifactPart(BaseModel):
    kind: str
    text: str | None = None
    data: Any | None = None


class Artifact(BaseModel):
    artifactId: str
    name: str
    parts: list[ArtifactPart]


class RpcResult(BaseModel):
    id: str
    contextId: str
    status: ResponseStatus
    artifacts: list[Artifact]
    kind: Literal["task"]


class RpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    result: RpcResult | None = None
    error: RpcError | None = None
