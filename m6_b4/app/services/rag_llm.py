"""Настройки моделей для OpenAI Responses в LlamaIndex."""

from typing import Any

from llama_index.llms.openai import OpenAIResponses

from app.services.request_options import response_options


class OpenAIResponsesLLM(OpenAIResponses):
    def _get_model_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        options = super()._get_model_kwargs(**kwargs)
        temperature = options.pop("temperature", None)
        model_options = response_options(self.model, temperature=temperature)
        if "reasoning" in model_options:
            options.pop("top_p", None)
        options.update(model_options)
        return options
