"""Клиент LLM с retry (tenacity) и fallback.

Все провайдеры работают через OpenAI-совместимый API.
Цепочка: primary → fallback → эскалация на оператора.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI, RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from config import Settings
from models import Category, LLMResult
from core.classification import heuristic_classify

# Ответ-заглушка, когда ни один провайдер не дал полезный ответ
FALLBACK_ANSWER = "Передаю вопрос специалисту."


def _build_client(api_key: str | None, base_url: str | None) -> OpenAI | None:
    """Создаёт OpenAI-совместимый клиент, если есть ключ."""
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)


class RobustLLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.primary = _build_client(settings.api_key, settings.base_url)
        self.fallback = _build_client(settings.fallback_api_key, settings.fallback_base_url)

    # ── Цепочка провайдеров ───────────────────────────────────────────

    def _provider_chain(self) -> Iterator[tuple[OpenAI, str, bool]]:
        """Отдаёт (client, model, used_fallback) для каждого доступного провайдера."""
        if self.primary is not None:
            yield self.primary, self.settings.primary_model, False
        if self.fallback is not None and self.settings.fallback_model:
            yield self.fallback, self.settings.fallback_model, True

    # ── Публичные методы ──────────────────────────────────────────────

    def classify(self, messages: list[dict[str, str]]) -> Category:
        """Классифицирует запрос: primary → fallback → эвристика."""
        for client, model, _ in self._provider_chain():
            try:
                raw = self._call(client, model, messages, temperature=0, max_tokens=8)
                return Category(raw.strip().lower())
            except Exception:
                continue

        return heuristic_classify(messages[-1]["content"])

    def answer(self, messages: list[dict[str, Any]]) -> LLMResult:
        """Получает ответ: primary → fallback → эскалация."""
        for client, model, used_fallback in self._provider_chain():
            try:
                if used_fallback:
                    logger.info("Переключаюсь на fallback: {}", model)
                text, tokens = self._answer_from(client, model, messages)
                return LLMResult(
                    text, tokens,
                    "fallback" if used_fallback else "primary",
                    model, used_fallback,
                )
            except Exception as e:
                logger.warning("Провайдер {} недоступен: {}", model, e)

        # Все провайдеры недоступны — переводим на оператора
        return LLMResult(FALLBACK_ANSWER, 0, "escalation", "none", True)

    def transcribe(self, audio_path: str, stt_model: str) -> str:
        """STT: аудиофайл → текст через audio.transcriptions."""
        client = self.primary or self.fallback
        if client is None:
            return ""
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model=stt_model,
                file=f,
                language="ru",
                response_format="text",
            )
        return transcript.text if hasattr(transcript, "text") else str(transcript)

    def speak(self, text: str, tts_model: str, voice: str, output_path: str) -> str:
        """TTS: текст → аудиофайл через audio.speech."""
        client = self.primary or self.fallback
        if client is None:
            return ""
        response = client.audio.speech.create(
            model=tts_model,
            voice=voice,
            input=text,
        )
        response.stream_to_file(output_path)
        return output_path

    def generate_image(
        self, prompt: str, model: str, output_path: str,
    ) -> str:
        """Генерация изображения через OpenAI images.generate."""
        client = self.primary or self.fallback
        if client is None:
            return ""
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size="1024x1024",
            quality="auto",
            n=1,
            output_format="png",
        )
        image_b64 = response.data[0].b64_json
        if image_b64:
            Path(output_path).write_bytes(base64.b64decode(image_b64))
            return output_path
        return ""

    # ── Внутренние методы ─────────────────────────────────────────────

    def _answer_from(
        self, client: OpenAI, model: str, messages: list[dict[str, Any]],
    ) -> tuple[str, int]:
        """Один ответ от провайдера. Возвращает (текст, токены)."""
        text = self._call(client, model, messages)
        return (text or FALLBACK_ANSWER), 0

    def _call(
        self,
        client: OpenAI,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 250,
    ) -> str:
        """Вызов LLM с retry через tenacity (экспоненциальная задержка)."""

        @retry(
            wait=wait_exponential(multiplier=1, min=1, max=60),
            stop=stop_after_attempt(self.settings.retry_attempts),
            retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        )
        def _do() -> str:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.settings.request_timeout_seconds,
            )
            return (response.choices[0].message.content or "").strip()

        return _do()
