"""Главный модуль бизнес-логики ассистента поддержки.

Класс ``SupportAssistantApp`` оркестрирует весь цикл обработки запроса:
классификация → проверка кеша → вызов LLM (с retry/fallback) → эскалация →
ведение истории → логирование.
"""

from __future__ import annotations

import time
from uuid import uuid4

from loguru import logger

from config import Settings
from models import AssistantResponse, SessionStats
from infrastructure.cache import RedisCache
from infrastructure.llm import FALLBACK_ANSWER, RobustLLMClient
from prompts.loader import build_answer_messages, build_classifier_messages, build_system_prompt
from core.classification import should_escalate


class SupportAssistantApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.system_prompt = build_system_prompt(settings.service_name)
        self.history: list[dict[str, str]] = []
        self.failed_attempts = 0
        self.stats = SessionStats()
        self.cache = RedisCache(settings.redis_host, settings.redis_port, settings.redis_ttl)
        self.client = RobustLLMClient(settings)

        # Логирование только в файл (убираем дефолтный вывод в stderr)
        logger.remove()
        logger.add(settings.log_path, format="{time} {message}", rotation="10 MB")

    def handle_command(self, command: str) -> str | None:
        if command == "/clear":
            self.history.clear()
            self.failed_attempts = 0
            return "История очищена."
        if command == "/clear_cache":
            deleted = self.cache.clear()
            return f"Кеш очищен. Удалено ключей: {deleted}."
        if command == "/reset_redis_stats":
            self.cache.reset_stats()
            return "Статистика Redis сброшена."
        if command == "/stats":
            cache_info = self.cache.stats()
            return (
                f"Запросов: {self.stats.total_queries} | "
                f"LLM вызовов: {self.stats.llm_calls} | "
                f"Токенов: {self.stats.total_tokens} | "
                f"Эскалаций: {self.stats.escalations} | "
                f"Redis: {cache_info['keys']} ключей, "
                f"hit rate: {cache_info['hit_rate']} "
                f"({cache_info['hits']}/{cache_info['hits'] + cache_info['misses']})"
            )
        if command == "/quit":
            return None
        return "Доступные команды: /clear, /clear_cache, /reset_redis_stats, /stats, /quit"

    def respond(self, user_message: str, image_path: str | None = None) -> AssistantResponse:
        started_at = time.perf_counter()
        self.stats.total_queries += 1

        category = self.client.classify(build_classifier_messages(user_message))

        if should_escalate(
            user_message=user_message,
            category=category,
            failed_attempts=self.failed_attempts,
        ):
            self.stats.escalations += 1
            self.failed_attempts = 0
            text = f"Передаю вопрос специалисту. Номер обращения: {uuid4().hex[:8].upper()}."
            latency = time.perf_counter() - started_at
            self._log(user_message, category, text, 0, latency, False, "router", "escalation")
            return AssistantResponse(text, category, False, latency, "router", "escalation", False)

        # При наличии изображения пропускаем кеш
        if not image_path:
            cached = self.cache.get(user_message)
            if cached is not None:
                self.stats.cache_hits += 1
                self._remember_turn(user_message, cached)
                latency = time.perf_counter() - started_at
                self._log(user_message, category, cached, 0, latency, True, "cache", "cache")
                return AssistantResponse(cached, category, True, latency, "cache", "cache", False)

        self.stats.cache_misses += 1
        self.stats.llm_calls += 1
        messages = build_answer_messages(self.system_prompt, self.history, user_message, image_path)
        result = self.client.answer(messages)
        if not image_path:
            self.cache.set(user_message, result.text)

        if result.text.strip() == FALLBACK_ANSWER:
            self.failed_attempts += 1
        else:
            self.failed_attempts = 0

        latency = time.perf_counter() - started_at
        self._remember_turn(user_message, result.text)
        self.stats.total_tokens += result.tokens
        self._log(
            user_message, category, result.text,
            result.tokens, latency, False, result.provider, result.model,
        )
        return AssistantResponse(
            result.text, category, False, latency,
            result.provider, result.model, result.used_fallback,
        )

    def transcribe(self, audio_path: str) -> str:
        """STT: аудиофайл → текст."""
        return self.client.transcribe(audio_path, self.settings.stt_model)

    def speak(self, text: str, output_path: str = "response.mp3") -> str:
        """TTS: текст → аудиофайл."""
        return self.client.speak(
            text, self.settings.tts_model, self.settings.tts_voice, output_path,
        )

    def generate_image(self, prompt: str, output_path: str = "generated.png") -> str:
        """Генерация изображения через OpenAI images.generate."""
        return self.client.generate_image(
            prompt, self.settings.imagegen_model, output_path,
        )

    def _remember_turn(self, user_message: str, answer: str) -> None:
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > self.settings.history_limit:
            self.history = self.history[-self.settings.history_limit :]

    def _log(
        self,
        user_message: str,
        category: str,
        answer: str,
        tokens: int,
        latency_seconds: float,
        from_cache: bool,
        provider: str,
        model: str,
    ) -> None:
        logger.info(
            "{cat} | {prov}/{mod} | {tok} tok | {lat:.3f}s | cache={cache} | Q: {msg} | A: {ans}",
            cat=category,
            prov=provider,
            mod=model,
            tok=tokens,
            lat=latency_seconds,
            cache=from_cache,
            msg=user_message[:100],
            ans=answer[:100],
        )
