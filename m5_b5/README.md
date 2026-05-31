# Корпоративный RAG — FastAPI + Qdrant + LlamaIndex

Образцовая реализация для блока «Корпоративный RAG». Это снимок **одного сквозного
сервиса**, который растёт от чекпоинта к чекпоинту: чат-ядро на FastAPI, тонкий
Telegram-бот, Qdrant как векторное хранилище, ответ по базе знаний с цитатами на
источники. На этом шаге сервис обрастает **корпоративной обвязкой**: документы
загружаются и переиндексируются через ручки, индексация вынесена в отдельный
конвейер, а RAG-запросы логируются для аналитики.

## Что нового на этом чекпоинте

Относительно предыдущего снимка (RAG-ответ с цитатами уже работал через
`POST /rag/query`) добавлена корпоративная обвязка: **ручки для документов**,
**офлайн-конвейер индексации**, **аналитика RAG-запросов** — и сам **путь RAG стал
умнее**: широкий поиск, опциональный реранкинг и честный отказ, если ничего
уверенного не нашлось.

| Что добавилось | Файл | Зачем |
|---|---|---|
| Ручки для документов | `app/routers/documents.py` | `POST /documents/upload` (загрузить файл) и `POST /documents/reindex` (переиндексировать корпус) — тяжёлая работа уходит в фон, ответ `202 queued` сразу |
| Конвейер индексации | `app/services/ingestion.py` | `IngestionService` на LlamaIndex `IngestionPipeline`: парсинг корпуса, обогащение метаданными из путей, инкрементальный `UPSERTS` по сохранённому docstore |
| Аналитика запросов | `migrations/versions/0003_rag_queries_sources.py` | таблица `rag_queries` (лог запросов: уверенность ответа и top-score) + колонка `chat_messages.sources` (цитаты рядом с ответом ассистента) |
| Умнее путь RAG | `app/services/rag.py`, `app/routers/rag.py` | широкий поиск → опциональный реранкинг → код-гард (честный отказ, если лучший score ниже порога) → синтез с нумерованными цитатами; ответ теперь содержит флаг `confident` и богатые цитаты `{id, file_name, snippet}` |
| Проверка | `tests/test_documents.py`, `tests/test_ingestion.py`, `tests/test_analytics.py` | ручки документов на фейковом индексаторе, чистые функции конвейера, лог запросов и пробелы в знаниях |

### Два контура

- **Онлайн (запрос):** `POST /rag/query` стал устойчивее — широкий поиск,
  опциональный реранкинг и честный отказ, если лучший score ниже порога (флаг
  `confident`). После ответа пишет строку в `rag_queries` (нормализованный вопрос,
  `confident`, `top_score`); сбой записи лога не роняет ответ пользователю.
- **Офлайн (индексация):** документ приходит через `POST /documents/upload`,
  сохраняется в корпус, а парсинг и эмбеддинг уходят в `BackgroundTasks`. Это
  отдельный `IngestionService`, который пишет в ту же коллекцию Qdrant, из которой
  читает `RAGService`. Для продакшена вместо `BackgroundTasks` — отдельный воркер
  (Celery/RQ/Dramatiq).

Конвейер индексации: `SimpleDirectoryReader` (с метаданными из путей: `department`,
`doc_type`, `version`, `visibility`) → `enrich` (чистка PDF-шума, исключение
технических полей из эмбеддинга) → `SentenceSplitter` → `OpenAIEmbedding` →
`QdrantVectorStore`. Docstore сохраняется на диск, поэтому повторный прогон
обновляет только изменённые документы, а не переэмбеддит весь корпус
(`DocstoreStrategy.UPSERTS`).

Аналитика читается через существующую админ-ручку `GET /chats/admin/stats`
(защита `X-Admin-Token`): к прежним агрегатам добавились `refusal_rate` (доля
неуверенных RAG-ответов за окно) и `knowledge_gaps` (топ вопросов без уверенного
ответа — что добавить в базу знаний).

## Куда смотреть

Если интересна именно корпоративная дельта этого чекпоинта — начинать здесь:

```
app/routers/documents.py       # POST /documents/upload, POST /documents/reindex
app/services/ingestion.py      # IngestionService: парсинг → метаданные → UPSERTS
app/routers/rag.py             # POST /rag/query + запись в rag_queries
app/admin/repository.py        # compute_stats: refusal_rate + knowledge_gaps
migrations/versions/0003_rag_queries_sources.py   # rag_queries + chat_messages.sources
```

Карта всего сервиса:

```
app/        серверная часть на FastAPI: chat/ (чат-ядро), routers/, services/,
            moderation/ (фильтр + модерация OpenAI), admin/, ratelimit/, observability/
bot/        тонкий Telegram-бот (aiogram 3.x); своей истории не хранит — единственный
            источник правды это серверная часть
data/       учебные корпуса (rag-block-03 — база для RAG)
migrations/ alembic (чаты, лимиты, отзывы, промпты, оповещения, лог RAG-запросов)
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

# 3) Запустить серверную часть (корпус проиндексируется при старте, если пуст)
uv run uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

При старте `lifespan` поднимает `IngestionService` и, если коллекция Qdrant пуста,
индексирует корпус один раз. На рестартах `UPSERTS` по сохранённому docstore
пропускает неизменённое.

## Проверить RAG

```bash
curl -s -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"За сколько дней можно вернуть деньги за подписку?"}'
# → {"answer":"...14 дней [1].","top_score":0.57,"confident":true,
#    "sources":[{"id":1,"file_name":"billing_refunds.md","score":0.57,"snippet":"..."}, ...]}
```

## Загрузить документ в базу знаний

```bash
# Файл сохраняется в корпус, индексация уходит в фон → 202 queued
curl -s -X POST http://localhost:8000/documents/upload \
  -F "file=@policy.pdf"
# → {"status":"queued","detail":"policy.pdf принят, индексация в фоне"}

# Переиндексировать корпус: incremental (по умолчанию) / full / files
curl -s -X POST http://localhost:8000/documents/reindex \
  -H "Content-Type: application/json" \
  -d '{"mode":"incremental"}'
# → {"status":"queued","detail":"режим incremental, индексация в фоне"}
```

Поддерживаемые форматы: `.pdf`, `.docx`, `.md`, `.txt`, `.html`. Через 30–60 секунд
новый документ появляется в индексе и доступен в ответах `POST /rag/query`. Упавший
при индексации файл изолируется в `.failed` и виден в логах.

## Аналитика RAG-запросов

```bash
TOKEN="$(grep ^ADMIN_TOKEN= .env | cut -d= -f2)"

curl -s -H "X-Admin-Token: $TOKEN" http://localhost:8000/chats/admin/stats
# → {..., "refusal_rate":0.12, "knowledge_gaps":["сброс пароля","оплата картой", ...]}
```

`refusal_rate` — доля запросов, на которые сервис честно ответил «не нашёл»;
`knowledge_gaps` — самые частые такие вопросы, то есть чего не хватает в базе.
Для этого нужен поднятый Postgres с накатанными миграциями (см. полный стек ниже).

## Проверить конвейер индексации против живого Qdrant

```bash
QDRANT_TEST_URL=http://localhost:6333 uv run python scripts/verify_rag.py
```

## Тесты

```bash
uv run pytest -q
```

Тесты идут без сети и без `OPENAI_API_KEY` (через `httpx.ASGITransport`): ручки
документов проверяются на фейковом индексаторе, чистые функции конвейера
(`clean`, `enrich`, метаданные из путей) — напрямую, лог запросов и пробелы в
знаниях — на фейковой сессии. Проверочные тесты Qdrant включаются переменной
`QDRANT_TEST_URL=http://localhost:6333`.

## Полный стек (серверная часть + бот + Redis + Postgres)

```bash
cp .env.example .env
# заполнить: LLM__OPENAI_API_KEY, BOT_TOKEN, BOT_ADMIN_IDS,
# ADMIN_TOKEN и INTERNAL_TOKEN (openssl rand -hex 32), ADMIN_CHAT_ID
docker compose up -d --build
docker compose exec app alembic upgrade head   # включая 0003 — rag_queries + sources
```
