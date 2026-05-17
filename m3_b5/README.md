## Что внутри

```
app/
├── main.py              # FastAPI app + lifespan + middleware + exception handlers
├── core/
│   ├── config.py        # Settings (pydantic-settings v2, nested LLMSettings)
│   └── exceptions.py    # LLMError + 4 подкласса
├── deps/
│   └── providers.py     # get_llm, get_cache, get_llm_service + Annotated aliases
├── routers/
│   ├── chat.py          # /chat, /chat/stream (SSE), /chat/batch
│   ├── models.py        # /models — каталог с ценами
│   └── health.py        # /health, /ready
├── services/
│   └── llm.py           # LLMService: complete, stream, кеш, retry, маппинг ошибок
└── schemas/
    ├── chat.py          # Message, ChatRequest, ChatResponse, Usage, ChatDelta,
    │                    # OpenAIParams/OllamaParams (discriminated union)
    └── models.py        # ModelInfo
tests/
├── conftest.py          # mock_llm, mock_cache, AsyncClient через ASGITransport
├── test_chat.py         # 10 тестов: happy path, валидация, batch, кеш
├── test_health.py       # /health, /ready (up/down)
├── test_models.py       # /models
└── test_stream.py       # SSE через client.stream + fake async-generator
```

## Запуск

Нужен `uv` (`brew install uv` или `pip install uv`) и Python 3.12 (uv подтянет сам).

```bash
uv sync
cp .env.example .env       # подставить настоящий LLM__OPENAI_API_KEY для боевых вызовов

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI — http://localhost:8000/docs
- ReDoc      — http://localhost:8000/redoc
- OpenAPI    — http://localhost:8000/openapi.json

Redis опционален: если на `REDIS_URL` никто не отвечает, lifespan ловит ошибку
и поднимается без кеша (запись `Redis недоступен … — продолжаем без кеша`).
`/health` всегда `200 {"status":"ok"}` (liveness, процесс жив).
`/ready` отдаёт `200 {"status":"ok","redis":"up"}` либо `503 {"status":"degraded","redis":"down"}`.

## Запуск через Docker (Б3.5)

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps                    # оба сервиса healthy через ~15 сек
curl -s http://localhost:8000/health  # 200 {"status":"ok"}
curl -s http://localhost:8000/ready   # 200 {"status":"ok","redis":"up"}
docker compose exec app id            # uid=1000(appuser) — non-root
docker compose exec redis redis-cli ping
docker compose down                   # остановить (данные redis сохранятся)
docker compose down -v                # + удалить volume redis_data
```

`compose.override.yaml` подмерживается автоматически в dev: даёт `--reload`,
bind-mount `./app:/app/app:ro` и проброс `redis:6379` на хост для `redis-cli`.
В проде override не выкладывается — работает только `compose.yaml`.

Замеры на 2026-05 (amd64, полный production-stack):

| Этап                                  | Размер  |
|---------------------------------------|---------|
| `python:3.13` + `COPY . .` + `pip`    | ~1150 MB |
| `python:3.13-slim-bookworm` + `pip`   | ~220 MB |
| slim + multi-stage + `uv 0.11.x` (наш Dockerfile) | ~190 MB |
| Первая сборка `--no-cache`            | ~50 сек |
| Rebuild после правки `app/`           | 2–3 сек |

## Тесты

```bash
uv run pytest -v
```

Все тесты используют `httpx.AsyncClient` + `ASGITransport` + `dependency_overrides`,
никуда не ходят по сети — `OPENAI_API_KEY` для прогона тестов не нужен.

Ожидаемый вывод: `16 passed`.

## Примеры HTTP-вызовов

### Синхронный чат

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "Ты лаконичный ассистент."},
      {"role": "user",   "content": "Скажи привет одним словом."}
    ],
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 50
  }'
```

В ответе клиент получает `X-Request-ID` и `X-LLM-Cost-USD` в заголовках.

### Streaming через SSE

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"считай до 5"}]}'
```

Поток событий: `data: {"content":"..."}\n\n` … `data: {"usage":{...}}\n\n` … `data: [DONE]`.

### Batch

```bash
curl -s -X POST http://localhost:8000/chat/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"messages":[{"role":"user","content":"1+1"}]},
    {"messages":[{"role":"user","content":"2+2"}]}
  ]'
```

Возвращает `list[ChatResponse | {"error": ..., "detail": ...}]` — упавшие элементы
не ломают весь батч. Максимум 20 элементов, иначе 413.

### Каталог моделей / health

```bash
curl -s http://localhost:8000/models
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

## Конфиг

Переменные окружения (см. `.env.example`). Префиксы вложенных секций — через `__`:

| Переменная                  | Значение по умолчанию  |
|-----------------------------|------------------------|
| `APP_NAME`                  | `llm-service`          |
| `DEBUG`                     | `false`                |
| `CORS_ORIGINS`              | `["*"]`                |
| `REDIS_URL`                 | `redis://localhost:6379/0` |
| `CACHE_TTL_SECONDS`         | `3600`                 |
| `LLM__OPENAI_API_KEY`       | — (обязательна для боевых вызовов) |
| `LLM__DEFAULT_MODEL`        | `gpt-4o-mini`          |
| `LLM__REQUEST_TIMEOUT`      | `30.0`                 |
| `LLM__MAX_RETRIES`          | `3`                    |
