"""Адаптер моделей Chat Completions с явно заданными метаданными."""

from typing import Any

from llama_index.llms.openai_like import OpenAILike

from app.services.request_options import completion_options


class OpenAIChatLLM(OpenAILike):
    def _get_model_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        options = super()._get_model_kwargs(**kwargs)
        max_tokens = options.pop("max_tokens", None)
        temperature = options.pop("temperature", None)
        options.update(completion_options(self.model, max_tokens, temperature))
        return options
