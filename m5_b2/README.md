# llm-service + Telegram-бот + Qdrant (M5Б2)

Чат-сервис (FastAPI + Postgres) + тонкий Telegram-бот + Qdrant для RAG.
Развитие M4Б4: к чат-ядру добавлен `app/services/vector_store.py` — обёртка
над `AsyncQdrantClient`, плюс скрипты загрузки и сравнения метрик для
ДЗ Б5.2.

## Quick start (M5Б2)

```bash
# 1) Поднимаем Qdrant
docker compose up -d qdrant
# Дашборд: http://localhost:6333/dashboard

# 2) Зависимости
uv sync

# 3) Сгенерировать учебный корпус (120 SaaS-FAQ-чанков)
python data/generate_sample.py

# 4) Залить в Qdrant (нужен LLM__OPENAI_API_KEY в .env)
python scripts/load_to_qdrant.py
# → создаст коллекцию documents, зальёт 120 точек с payload-индексами

# 5) Сравнить ранжирование cosine vs dot
python scripts/compare_metrics.py
# → docs/metric_comparison.json + строки в консоль

# 6) Smoke-тесты модуля
QDRANT_TEST_URL=http://localhost:6333 uv run pytest tests/test_vector_store.py -v

# 7) Проверка, что весь код из презентации работает на текущем qdrant-client
QDRANT_TEST_URL=http://localhost:6333 uv run python scripts/verify_presentation.py
```

## Что добавлено в M5Б2

```
app/services/vector_store.py   # VectorStore — обёртка над AsyncQdrantClient
app/services/embeddings.py     # OpenAI embeddings (батчевый клиент)
scripts/load_to_qdrant.py      # идемпотентная загрузка (UUID5 по source+chunk_index)
scripts/compare_metrics.py     # cosine vs dot — два временных индекса, удаление после
scripts/verify_presentation.py # импорты + сценарии из всех code-слайдов презы
data/generate_sample.py        # синтетический корпус (120 FAQ про SaaS-поддержку)
data/sample_kb.jsonl           # сам корпус (на дипломе заменяется на свои данные)
tests/test_vector_store.py     # 8 smoke-тестов — требуют QDRANT_TEST_URL
docs/vector_store.md           # шаблон отчёта по ДЗ
```

В `compose.yaml` добавлен сервис `qdrant` (порты 6333/6334, named volume
`qdrant_storage`, healthcheck по TCP). В `app/main.py` lifespan создаёт
`VectorStore` и вызывает `ensure_collection`. В `app/deps/providers.py`
добавлен `VectorStoreDep` для DI в роуты (на Б5.3 он подключится к
LlamaIndex с тем же контрактом).

## Что внутри

```
app/                            # FastAPI backend
├── main.py                     # lifespan (LLM/Redis/Postgres), middleware, exception map
├── core/config.py              # Settings (pydantic-settings v2, nested LLMSettings)
├── deps/providers.py           # SessionFactoryDep, LLMDep, CacheDep, LLMServiceDep
├── routers/
│   ├── chat.py                 # /chat, /chat/stream (SSE), /chat/batch
│   ├── models.py               # /models — каталог с ценами
│   └── health.py               # /health, /ready
├── services/
│   ├── llm.py                  # LLMService: complete/stream, кеш, retry, mapping
│   ├── broadcaster.py          # admin → bot:9000/notify, fan-out с throttle
│   ├── notifier.py             # одиночный notify через bot /notify
│   ├── alerter.py              # alerts: fire / fetch / ack (БД-очередь)
│   └── handoff.py              # set_handoff_status_by_owner
├── chat/                       # доменная логика chat-сервиса
│   ├── domain.py               # Chat / ChatMessage (Pydantic + UUID)
│   ├── repository.py           # Protocol ChatRepository
│   ├── repositories/
│   │   ├── json_repo.py        # JSONL append-only
│   │   ├── pg_models.py        # SQLAlchemy table defs (chats / chat_messages)
│   │   └── pg_repo.py          # Postgres backend
│   ├── prompts/                # SystemPromptRepository + A/B traffic split
│   ├── service.py              # ChatService: send_message (SSE), check_input, A/B
│   ├── media.py                # image/voice/PDF/DOCX → OpenAI content-part
│   ├── deps.py                 # ChatServiceDep, RepositoryDep
│   └── routes.py               # /chats, /chats/{id}/messages (SSE), feedback
├── admin/
│   ├── routes.py               # /chats/admin/* (защита X-Admin-Token)
│   ├── repository.py           # AdminRepository: stats / export / owner_ids by interface
│   └── schemas.py              # StatsOut, BroadcastIn, ExportResult, AlertOut...
├── moderation/                 # двухслойный каскад (regex + OpenAI Moderation)
├── ratelimit/                  # token-bucket per owner_external_id (Postgres UPSERT)
├── observability/pii.py        # маскирование PII при экспорте
└── schemas/                    # request/response модели для /chat
bot/                            # Telegram-бот (aiogram 3.x)
├── __main__.py                 # polling + uvicorn(/notify) + drain_alerts в одном loop
├── config.py                   # BotSettings (pydantic-settings)
├── handlers/
│   ├── commands.py             # /start /help /clear /cancel
│   ├── text.py                 # свободный текст → backend SSE
│   ├── media.py                # фото / голос / документ
│   ├── fsm.py                  # /ask — wizard через FSM
│   ├── admin.py                # /stats, /broadcast — только для BOT_ADMIN_IDS
│   ├── handoff.py              # /operator — запрос юзера на оператора
│   └── feedback.py             # up/down callback под ответом
├── keyboards/inline.py         # feedback-клавиатура
├── services/
│   ├── backend_client.py       # async-клиент к /chats/* + admin endpoint'ам
│   ├── streaming.py            # SSE → sendMessageDraft, fallback на edit_text
│   ├── typing.py               # «бот печатает...» до прихода первого токена
│   ├── error_handling.py       # mapping httpx.HTTPStatusError → user-facing
│   └── alert_drain.py          # фон-таска: backend /alerts → admin-чат
├── states.py                   # AskFlow (FSM)
└── web.py                      # FastAPI /notify (защита X-Internal-Token)
migrations/                     # alembic
├── env.py
└── versions/
    ├── 0001_chats.py           # chats + chat_messages
    └── 0002_production.py      # rate_limits, feedback, prompts, alerts, broadcasts
tests/                          # pytest-asyncio, httpx.ASGITransport, без сети
├── conftest.py
├── test_chat.py / test_stream.py / test_models.py / test_health.py
├── test_admin.py / test_moderation.py / test_pii.py / test_prompts.py / test_ratelimit.py
├── chat/                       # routes / service / repository-contract / media / moderation
└── bot/                        # backend_client (MockTransport), fsm, web
```

## Запуск

Нужен `uv` (`brew install uv` или `pip install uv`), Python 3.12+ (uv подтянет сам).

### Локально (только backend, без бота)

```bash
uv sync
cp .env.example .env       # подставить LLM__OPENAI_API_KEY для боевых вызовов
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI — http://localhost:8000/docs
- OpenAPI    — http://localhost:8000/openapi.json
- `/health`  — всегда 200 (liveness)
- `/ready`   — 200/503 в зависимости от Redis

Redis и Postgres опциональны для боевых вызовов: если их нет на старте,
lifespan ловит ошибку и поднимается без них (кеш отключается, репозиторий
переключается в `CHAT_REPOSITORY=json` режим).

### Полный стек через Docker (backend + bot + redis + postgres)

```bash
cp .env.example .env
# Заполнить: LLM__OPENAI_API_KEY, BOT_TOKEN, BOT_ADMIN_IDS,
# ADMIN_TOKEN (openssl rand -hex 32), INTERNAL_TOKEN (то же),
# ADMIN_CHAT_ID (свой telegram user id для алертов в личку)

docker compose up -d --build
docker compose ps                     # все сервисы healthy через ~15 сек
docker compose exec app alembic upgrade head   # накатить миграции
docker compose logs -f bot            # увидеть «Bot starting ...»
```

`compose.override.yaml` подмерживается автоматически в dev: `--reload`,
bind-mount `./app:/app/app:ro` и проброс `redis:6379` / `postgres:5432` на хост.

## Тесты

```bash
uv run pytest -q
```

Все тесты используют `httpx.AsyncClient + ASGITransport` (для backend) и
`httpx.MockTransport` (для bot-клиента) — сети нет, `OPENAI_API_KEY` для прогона
не нужен. Ожидаемый вывод: `100 passed, 1 skipped`.

## Примеры HTTP-вызовов

### Создать чат / послать сообщение (SSE)

```bash
# 1. Идемпотентно создать чат (или получить существующий по owner+interface)
curl -s -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"owner_external_id":"u-42","interface":"telegram"}'
# → {"chat_id":"<uuid>"}

# 2. Стримить ответ
curl -N -X POST "http://localhost:8000/chats/<uuid>/messages" \
  -H "X-Owner-External-Id: u-42" \
  -F content="Привет, расскажи про себя одним предложением"
# data: {"type":"token","delta":"..."}\n\n
# data: {"type":"message_saved","message_id":"<uuid>"}\n\n
# data: {"type":"done"}\n\n
```

### Admin-API (нужен X-Admin-Token)

```bash
TOKEN="$(grep ^ADMIN_TOKEN= .env | cut -d= -f2)"

curl -s -H "X-Admin-Token: $TOKEN" http://localhost:8000/chats/admin/stats
curl -s -H "X-Admin-Token: $TOKEN" -X POST http://localhost:8000/chats/admin/broadcast \
  -H "Content-Type: application/json" \
  -d '{"text":"Тех-работы в 02:00","interface":"telegram"}'
curl -s -H "X-Admin-Token: $TOKEN" "http://localhost:8000/chats/admin/alerts"
```

### Bot-команды в Telegram

- `/start` / `/help` / `/clear` / `/cancel` — базовые
- `/ask` — wizard (FSM): выбор темы → вопрос → подтверждение
- `/operator` — запрос на handoff (юзер ↔ оператор)
- `/stats`, `/broadcast <текст>` — только для BOT_ADMIN_IDS
- Под каждым ответом — feedback-кнопки (up/down), идут в backend через
  POST `/chats/{id}/messages/{msg_id}/feedback`

## Архитектурные решения

- **Тонкий бот.** Bot не хранит истории/контекста — backend единственная
  точка истины. Это позволит позже подключить web-чат и звонилку без
  дублирования логики.
- **SSE-контракт стабильный** (`{type:"token",delta:...}` / `{type:"message_saved",...}` / `{type:"done"}`).
  Клиент пишется один раз, формат не меняется.
- **Pull-модель алертов.** Backend пишет строку в `alerts` через `fire_alert(...)`,
  бот раз в 10 секунд пуллит и шлёт в админ-чат. Без message broker'а — у нас
  уже есть Postgres. Гарантия at-least-once через `acked_at`.
- **Модерация → 403 ДО старта streaming.** `check_input` вызывается из route
  handler'а, а не из SSE-генератора — иначе после старта `text/event-stream`
  HTTPException не сменит 200-статус.
- **Native multimodal.** Изображения уходят `image_url`-part'ом в основной
  `chat.completions.create` без отдельного Vision-вызова; голос — Whisper-1.

## Конфиг (см. `.env.example`)

Все переменные с `__` — это nested секции pydantic-settings (`LLM__OPENAI_API_KEY`
→ `Settings.llm.openai_api_key`).
