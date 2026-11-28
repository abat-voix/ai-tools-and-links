"""Совместимые параметры новых моделей для RAGAS и генератора датасета."""
from typing import Any

from llama_index.core.base.llms.types import LLMMetadata
from llama_index.llms.anthropic import Anthropic
from ragas.llms.base import InstructorLLM

from app.services.request_options import response_options


def is_current_claude(model: str) -> bool:
    return model.startswith(("claude-sonnet-5", "claude-opus-5", "claude-haiku-5", "claude-fable-5"))


class ModelAwareJudge(InstructorLLM):
    """Параметры судьи для выбранного API и семейства моделей."""

    def _map_provider_params(self) -> dict[str, Any]:
        if self.provider == "openai" and self.model.startswith("gpt-6"):
            options = response_options(
                self.model, self.model_args.get("max_tokens", 4096),
                self.model_args.get("temperature", 0),
            )
            return {**options, "store": False}

        options = super()._map_provider_params()
        if self.provider == "openai":
            if "max_completion_tokens" in options:
                options["max_output_tokens"] = options.pop("max_completion_tokens")
                options.pop("temperature", None)
            elif "max_tokens" in options:
                options["max_output_tokens"] = options.pop("max_tokens")
            options["store"] = False
        if self.provider == "anthropic" and is_current_claude(self.model):
            for name in ("temperature", "top_p", "top_k"):
                options.pop(name, None)
        return options


class TestsetAnthropic(Anthropic):
    """Явные метаданные Claude 5 до обновления реестра LlamaIndex."""

    @property
    def metadata(self) -> LLMMetadata:
        if not is_current_claude(self.model):
            return super().metadata
        return LLMMetadata(
            context_window=1_000_000, num_output=self.max_tokens,
            is_chat_model=True, model_name=self.model, is_function_calling_model=True,
        )

    @property
    def _model_kwargs(self) -> dict[str, Any]:
        options = super()._model_kwargs
        if is_current_claude(self.model):
            for name in ("temperature", "top_p", "top_k"):
                options.pop(name, None)
        return options
