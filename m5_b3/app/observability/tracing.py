"""Трейсинг LlamaIndex в Phoenix через OpenInference (опциональный runtime-путь).

Включается флагом `PHOENIX_ENABLED=true` и группой зависимостей `tracing`
(`uv sync --extra tracing`): openinference-instrumentation-llama-index +
opentelemetry-sdk + opentelemetry-exporter-otlp. По умолчанию выключено —
сервис поднимается без трейсинга, спаны не пишутся.

Инструментор подключается один раз при старте (lifespan) до сборки RAG-индекса;
дальше все вызовы LlamaIndex (retrieve, embed, LLM) попадают в спаны автоматически.
"""

import logging
from importlib.util import find_spec

from app.core.config import Settings

logger = logging.getLogger(__name__)


def setup_tracing(settings: Settings) -> bool:
    """Регистрирует LlamaIndexInstrumentor → Phoenix. True, если трейсинг включён."""
    if not settings.phoenix_enabled:
        return False
    if find_spec("openinference.instrumentation.llama_index") is None:
        logger.warning(
            "phoenix_enabled=true, но пакеты трейсинга не установлены — "
            "uv sync --extra tracing"
        )
        return False

    from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.phoenix_collector_endpoint))
    )
    trace.set_tracer_provider(provider)
    LlamaIndexInstrumentor().instrument(tracer_provider=provider)
    logger.info("Phoenix-трейсинг включён: %s", settings.phoenix_collector_endpoint)
    return True
