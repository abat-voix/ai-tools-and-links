from typing import Annotated, Literal

from openai.types.responses import ResponseUsage
from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=8_000)]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: Annotated[list[Message], Field(min_length=1, max_length=20)]
    cache: bool = False


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    @classmethod
    def from_response(cls, usage: ResponseUsage | None) -> "Usage":
        if usage is None:
            return cls()
        return cls(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached_tokens=usage.input_tokens_details.cached_tokens,
        )


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Usage
    cached: bool = False
