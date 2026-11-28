"""Выбор API и reasoning-параметров модели для tool calling."""
from langchain_openai import ChatOpenAI

from app.services.request_options import response_options


def build_agent_model(settings, **kwargs):
    model = settings.llm.default_model
    options = response_options(model, temperature=0)
    options["use_responses_api"] = True
    return ChatOpenAI(
        model=model, api_key=settings.llm.openai_api_key.get_secret_value(),
        timeout=settings.llm.request_timeout, **options, **kwargs,
    )


def validate_model_response(response):
    """Не исполнять частичные tool calls и не выдавать обрывок за готовый ответ."""
    metadata = response.response_metadata
    status = metadata.get("status")
    finish = metadata.get("finish_reason")
    if (status is not None and status != "completed") or (
        finish is not None and finish not in {"stop", "tool_calls"}
    ):
        raise ValueError(f"LLM did not complete: status={status}, finish_reason={finish}")
    if response.invalid_tool_calls:
        raise ValueError("LLM returned invalid tool calls")
    if not response.tool_calls and not str(response.text).strip():
        raise ValueError("LLM returned no text or tool calls")
    return response
