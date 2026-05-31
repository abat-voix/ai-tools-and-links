# Чат-сервис с RAG — FastAPI + Qdrant + LlamaIndex

Образцовая реализация для блока «Архитектура RAG». Это снимок **одного сквозного
сервиса**, который растёт от чекпоинта к чекпоинту: чат-ядро на FastAPI, тонкий
Telegram-бот, Qdrant как векторное хранилище, и на этом шаге — ответ по базе
знаний с цитатами на источники.

## Что нового на этом чекпоинте

Относительно предыдущего снимка (Qdrant уже поднят, но генерации ответа ещё нет)
добавлен **слой RAG**: вопрос → поиск релевантных фрагментов → ответ модели строго
по найденному контексту, со ссылками на источники.

| Что добавилось | Файл | Зачем |
|---|---|---|
| RAG на фреймворке | `app/services/rag.py` | `RAGService` на LlamaIndex поверх Qdrant: сборка индекса + ответ с цитатами |
| RAG «руками» | `app/services/rag_baremetal.py` | тот же сценарий на чистых `openai` + `qdrant-client` — видно, что именно берёт на себя LlamaIndex |
| Ручка ответа | `app/routers/rag.py` | `POST /rag/query`: вопрос на вход, ответ и источники на выход |
| Корпус знаний | `data/rag-block-03/` | учебная база из 10 документов (один заведомо нерелевантный — для проверки честного отказа) |
| Проверка | `scripts/verify_rag.py`, `tests/test_rag.py` | прогон пути RAG против живого Qdrant и модульные тесты |

Конвейер LlamaIndex: `SimpleDirectoryReader → SentenceSplitter → QdrantVectorStore
→ VectorStoreIndex → QueryEngine`. Индекс собирается один раз при старте приложения
(`lifespan` в `app/main.py`), доступ к сервису — через `RAGServiceDep` в
`app/deps/providers.py`. Остальная часть сервиса (чат, модерация, админка, бот) с
прошлого шага не менялась.

## Куда смотреть

Если интересен именно RAG этого чекпоинта — начинать здесь:

```
app/services/rag.py            # RAGService: сборка индекса + ответ с источниками
app/services/rag_baremetal.py  # тот же RAG без LlamaIndex — для сравнения
app/routers/rag.py             # POST /rag/query
app/services/vector_store.py   # обёртка над AsyncQdrantClient (с прошлого шага)
docs/rag.md                    # как устроен путь RAG подробно
```

Карта всего сервиса:

```
app/        серверная часть на FastAPI: chat/ (чат-ядро), routers/, services/,
            moderation/ (фильтр + модерация OpenAI), admin/, ratelimit/, observability/
bot/        тонкий Telegram-бот (aiogram 3.x); своей истории не хранит — единственный
            источник правды это серверная часть
data/       учебные корпуса (rag-block-03 — база для RAG)
migrations/ alembic (чаты, лимиты, отзывы, промпты, оповещения)
tests/      pytest-asyncio, httpx.ASGITransport — без обращения к сети
```

## Быстрый старт

Нужен [`uv`](https://docs.astral.sh/uv/) (`brew install uv` или `pip install uv`);
Python 3.12+ `uv` поставит сам.

```bash
# 1) Векторное хранилище
docker compose up -d qdrant          # панель: http://localhost:6333/dashboard

# 2) Зависимости и конфиг
uv sync
cp .env.example .env                  # вписать LLM__OPENAI_API_KEY

# 3) Запустить серверную часть (индекс RAG соберётся при старте)
uv run uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

## Проверить RAG

```bash
curl -s -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"За сколько дней можно вернуть деньги за подписку?"}'
# → {"answer":"...14 дней...","top_score":0.57,
#    "sources":[{"text":"...","source":"billing_refunds.md","score":0.57}, ...]}
```

Полный прогон пути RAG против живого Qdrant:

```bash
QDRANT_TEST_URL=http://localhost:6333 uv run python scripts/verify_rag.py
```

## Тесты

```bash
uv run pytest -q
```

Тесты идут без сети и без `OPENAI_API_KEY` (через `httpx.ASGITransport`).
Проверочные тесты Qdrant включаются переменной `QDRANT_TEST_URL=http://localhost:6333`.

## Полный стек (серверная часть + бот + Redis + Postgres)

```bash
cp .env.example .env
# заполнить: LLM__OPENAI_API_KEY, BOT_TOKEN, BOT_ADMIN_IDS,
# ADMIN_TOKEN и INTERNAL_TOKEN (openssl rand -hex 32), ADMIN_CHAT_ID
docker compose up -d --build
docker compose exec app alembic upgrade head
```
