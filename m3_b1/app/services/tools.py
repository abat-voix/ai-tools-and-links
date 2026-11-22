import json
from typing import Annotated

from openai.types.responses import ResponseFunctionToolCall, ToolParam
from openai.types.responses.response_input_item_param import FunctionCallOutput
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.tickets import get_ticket_status

TOOL_NAME = "get_ticket_status"
TOOLS: list[ToolParam] = [{
    "type": "function",
    "name": TOOL_NAME,
    "description": "Возвращает статус доступной пользователю заявки по её идентификатору.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {"ticket_id": {"type": "string"}},
        "required": ["ticket_id"],
        "additionalProperties": False,
    },
}]


class TicketArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: Annotated[str, Field(pattern=r"^T-[0-9]{4}$")]


def execute_tool(call: ResponseFunctionToolCall, user_id: str) -> FunctionCallOutput:
    result: dict[str, str] = {"error": "unknown_tool"}
    if call.name == TOOL_NAME:
        try:
            args = TicketArguments.model_validate_json(call.arguments)
        except ValidationError:
            result = {"error": "invalid_arguments"}
        else:
            status = get_ticket_status(user_id, args.ticket_id)
            result = {"status": status} if status else {"error": "not_found"}

    return {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": json.dumps(result),
    }
