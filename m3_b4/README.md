# LLM-сервис — FastAPI поверх облачного API

Образцовая реализация для блока «Архитектура ИИ-приложений: FastAPI-сервис для LLM».
Это снимок **одного сквозного сервиса**, который растёт от чекпоинта к чекпоинту.
Здесь — самый первый его шаг в зеркале: чат-ядро на FastAPI, которое оборачивает
асинхронного клиента OpenAI и выставляет его наружу как HTTP.

## Что нового на этом чекпоинте

До этого шага дипломный сервис жил как CLI-приложение поверх облачного API
(модули 1–2 курса): тот же асинхронный клиент вызывался из командной строки.
Здесь сервис **сменил форму** — из CLI стал веб-сервисом на FastAPI. Логика обращения
к модели переехала в слой `app/services/llm.py`, а вокруг неё выросла серверная
обвязка: ручки, внедрение зависимостей, кеш, единый формат ошибок.

| Что добавилось | Файл | Зачем |
|---|---|---|
| HTTP-поверхность | `app/routers/chat.py` | `POST /chat` (синхронный ответ), `POST /chat/stream` (потоковая выдача через SSE), `POST /chat/batch` (до 20 запросов за раз) |
| Слой работы с моделью | `app/services/llm.py` | `LLMService`: вызов OpenAI, кеш, повторные попытки на `tenacity`, перевод ошибок SDK в доменные исключения |
| Внедрение зависимостей | `app/deps/providers.py` | клиент, кеш и сервис достаются из `app.state` через `Annotated`-провайдеры — без глобальных переменных |
| Конфиг | `app/core/config.py` | `Settings` на pydantic-settings v2 с вложенной секцией `LLMSettings`; ключ читается как `SecretStr` |
| Единый формат ошибок | `app/main.py` | `lifespan` поднимает клиента и кеш; обработчики переводят доменные исключения и ошибки валидации в аккуратный JSON и нужный HTTP-код |
| Каталог и проверка живости | `app/routers/models.py`, `app/routers/health.py` | `GET /models` (цены, контекст), `GET /health` и `GET /ready` для проверки живости |

Клиент OpenAI и подключение к кешу поднимаются один раз при старте приложения
(`lifespan` в `app/main.py`), а ручки получают готовый `LLMService` через
`LLMServiceDep`. Кеш необязателен: если на `REDIS_URL` никто не отвечает, `lifespan`
ловит ошибку и сервис поднимается без кеша (пишет в лог `Redis недоступен … — продолжаем без кеша`),
а `GET /ready` отдаёт `{"status":"degraded"}`.

## Куда смотреть

Главное на этом шаге — как один вызов модели обрастает production-обвязкой.
Начинать здесь:

```
app/main.py             # сборка приложения: lifespan, middleware, обработчики ошибок
app/services/llm.py     # LLMService: вызов модели, кеш, повторы, маппинг ошибок
app/routers/chat.py     # POST /chat, /chat/stream (SSE), /chat/batch
app/deps/providers.py   # внедрение зависимостей: клиент, кеш, сервис из app.state
app/core/config.py      # Settings (pydantic-settings v2, вложенная LLMSettings)
app/schemas/chat.py     # ChatRequest / ChatResponse / ChatDelta / Usage
```

Карта снимка:

```
app/
├── main.py             # FastAPI-приложение + lifespan + middleware + обработчики ошибок
├── core/
│   ├── config.py       # Settings (вложенная LLMSettings, SecretStr)
│   └── exceptions.py   # LLMError + подклассы (rate limit, auth, timeout, модерация)
├── deps/providers.py   # провайдеры зависимостей + Annotated-алиасы
├── routers/            # chat.py, models.py, health.py
├── services/llm.py     # LLMService
└── schemas/            # chat.py, models.py
tests/                  # pytest + httpx.ASGITransport — без обращения к сети
```

## Быстрый старт

Нужен [`uv`](https://docs.astral.sh/uv/) (`brew install uv` или `pip install uv`);
Python 3.12+ `uv` поставит сам.

```bash
uv sync
cp .env.example .env                  # вписать LLM__OPENAI_API_KEY

uv run uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

Проверить синхронный чат:

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Скажи привет одним словом."}]}'
# → {"content":"Привет","model":"gpt-4o-mini","usage":{...},"cached":false, ...}
```

Потоковая выдача через SSE приходит кусками `data: {...}\n\n`, в конце — `data: [DONE]`:

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"считай до 5"}]}'
```

В ответ каждый запрос получает заголовок `X-Request-ID` для сквозной трассировки.

Кеш срабатывает только для детерминированных запросов: `LLMService.complete`
обращается к нему при `temperature == 0` и при поднятом Redis. Повторный такой
запрос возвращается с `cached: true` и заметно быстрее. При `temperature > 0`
ответ всегда идёт от модели.

## Конфиг

Переменные окружения (см. `.env.example`). Префикс вложенной секции — через `__`:

| Переменная | По умолчанию |
|---|---|
| `APP_NAME` | `llm-service-asdf` |
| `DEBUG` | `false` |
| `CORS_ORIGINS` | `["*"]` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `CACHE_TTL_SECONDS` | `3600` |
| `LLM__OPENAI_API_KEY` | — (нужна для реальных вызовов) |
| `LLM__DEFAULT_MODEL` | `gpt-4o-mini` |
| `LLM__REQUEST_TIMEOUT` | `30.0` |
| `LLM__MAX_RETRIES` | `3` |

## Тесты

```bash
uv run pytest -q
```

Тесты идут без сети и без `OPENAI_API_KEY`: приложение поднимается через
`httpx.ASGITransport`, а клиент OpenAI и кеш подменяются заглушками
(`dependency_overrides`). Ожидаемый вывод: `16 passed`.
