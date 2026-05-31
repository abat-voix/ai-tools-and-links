# Чат-сервис + векторное хранилище Qdrant — FastAPI + Postgres

Образцовая реализация для блока «Векторные базы данных». Это снимок **одного
сквозного сервиса**, который растёт от чекпоинта к чекпоинту: чат-ядро на
FastAPI, тонкий Telegram-бот, и на этом шаге — векторное хранилище: эмбеддинги,
заливка учебного корпуса в Qdrant и поиск по вектору с фильтрами.

## Что нового на этом чекпоинте

Относительно предыдущего снимка (чат + бот + Postgres + Redis) добавлено
**векторное хранилище**: документы превращаются в эмбеддинги, заливаются в
Qdrant и ищутся по похожести вектора с фильтрацией по метаданным. Генерации
ответа модели по найденному ещё нет — это следующий чекпоинт; здесь
выстраивается хранилище и поиск под него.

| Что добавилось | Файл | Зачем |
|---|---|---|
| Обёртка над Qdrant | `app/services/vector_store.py` | `VectorStore` поверх `AsyncQdrantClient`: коллекция, индексы, заливка, поиск по вектору |
| Эмбеддинги | `app/services/embeddings.py` | `EmbeddingsClient` поверх OpenAI: текст → вектор, батчами по 64 |
| Утилиты загрузки | `app/services/loader_utils.py` | детерминированный UUID5 по `(source, chunk_index)` + чтение JSONL |
| Заливка корпуса | `scripts/load_to_qdrant.py` | идемпотентная загрузка JSONL в Qdrant с индексами по метаданным |
| Сравнение метрик | `scripts/compare_metrics.py` | cosine и dot на одних векторах: совпадает ли ранжирование top-5 |
| Учебный корпус | `data/sample_kb.jsonl` | 120 фрагментов FAQ по техподдержке SaaS (20 источников, 6 категорий) |
| Проверка | `tests/test_vector_store.py` | проверочные тесты заливки и поиска против живого Qdrant |
| Шаблон отчёта | `docs/vector_store.md` | заготовка отчёта по ДЗ: метрика, фильтры, параметры HNSW |

В `compose.yaml` добавлен сервис `qdrant` (порты 6333/6334, named volume
`qdrant_storage`, healthcheck по TCP). При старте `app/main.py` создаёт
`VectorStore` и вызывает `ensure_collection`; если Qdrant недоступен —
серверная часть поднимается без него (доступ к хранилищу через `VectorStoreDep`
вернёт `None`). В `app/core/config.py` добавлены `qdrant_url`,
`qdrant_api_key`, `qdrant_collection`, `embedding_dim`, `embedding_model`.
Остальная часть сервиса (чат, модерация, админка, бот) с прошлого шага не
менялась.

## Куда смотреть

Если интересно именно векторное хранилище этого чекпоинта — начинать здесь:

```
app/services/vector_store.py   # VectorStore: коллекция, индексы по метаданным, upsert, search
app/services/embeddings.py     # EmbeddingsClient: текст → вектор поверх OpenAI
scripts/load_to_qdrant.py      # заливка корпуса в Qdrant (идемпотентная)
scripts/compare_metrics.py     # cosine vs dot на одних и тех же векторах
data/sample_kb.jsonl           # учебный корпус (на дипломе заменяется на свои данные)
docs/vector_store.md           # шаблон отчёта: метрика, фильтры, HNSW
```

Карта всего сервиса:

```
app/        серверная часть на FastAPI: chat/ (чат-ядро), routers/, services/,
            moderation/ (фильтр + модерация OpenAI), admin/, ratelimit/, observability/
bot/        тонкий Telegram-бот (aiogram 3.x); своей истории не хранит — единственный
            источник правды это серверная часть
data/       учебный корпус (sample_kb.jsonl) для заливки в Qdrant
migrations/ alembic (чаты, лимиты, отзывы, промпты, оповещения)
tests/      pytest-asyncio, httpx.ASGITransport — без обращения к сети
```

## Векторное хранилище: как устроено

`VectorStore` — тонкая обёртка над `AsyncQdrantClient`, чтобы остальной код не
зависел от деталей qdrant-client напрямую:

- `ensure_collection()` — создаёт коллекцию при отсутствии (`distance=COSINE`,
  HNSW `m=16`, `ef_construct=100`) и индексы по метаданным `source`, `created_at`,
  `category`. Если коллекция уже есть — проверяет размерность и падает с
  понятной ошибкой при расхождении, а не заливает мусор молча.
- `upsert(points, batch_size=256)` — заливает точки батчами, ждёт
  подтверждения только на последнем батче.
- `search(query_vector, top_k, query_filter)` — top-K точек по похожести через
  `query_points`, с фильтром по метаданным.

Каждый документ корпуса (`source`, `chunk_index`, `text`, `category`,
`created_at`) получает детерминированный id (`uuid5` по `source` + `chunk_index`)
— повторная заливка не плодит дубли. `EmbeddingsClient` гоняет тексты в OpenAI
батчами и возвращает по вектору на каждый текст в исходном порядке.

## Быстрый старт

Нужен [`uv`](https://docs.astral.sh/uv/) (`brew install uv` или `pip install uv`);
Python 3.12+ `uv` поставит сам.

```bash
# 1) Векторное хранилище
docker compose up -d qdrant          # панель: http://localhost:6333/dashboard

# 2) Зависимости и конфиг
uv sync
cp .env.example .env                  # вписать LLM__OPENAI_API_KEY

# 3) Залить учебный корпус в Qdrant
uv run python scripts/load_to_qdrant.py
# → создаст коллекцию documents, зальёт 120 точек с индексами по метаданным
```

Повторный запуск `load_to_qdrant.py` не плодит дубли: id точек
детерминированы, число точек в коллекции после второго прогона совпадает с
первым.

## Сравнить метрики

cosine и dot на одних и тех же векторах — совпадает ли ранжирование top-5
на пяти запросах:

```bash
uv run python scripts/compare_metrics.py
# → таблица в консоль + docs/metric_comparison.json
```

Скрипт собирает две временные коллекции (`documents_cosine`, `documents_dot`),
прогоняет запросы и удаляет временные коллекции после себя. На нормализованных
эмбеддингах OpenAI cosine и dot дают одинаковое ранжирование — это и есть
проверка корректности.

## Тесты

```bash
uv run pytest -q
```

Тесты идут без сети и без `OPENAI_API_KEY` (через `httpx.ASGITransport`).
Проверочные тесты Qdrant включаются переменной `QDRANT_TEST_URL`:

```bash
QDRANT_TEST_URL=http://localhost:6333 uv run pytest tests/test_vector_store.py -v
```

Они создают изолированные коллекции и проверяют заливку, поиск ближайшего
вектора, фильтры по строке/дате/числу и осмысленную ошибку при расхождении
размерности.

## Полный стек (серверная часть + бот + Redis + Postgres + Qdrant)

```bash
cp .env.example .env
# заполнить: LLM__OPENAI_API_KEY, BOT_TOKEN, BOT_ADMIN_IDS,
# ADMIN_TOKEN и INTERNAL_TOKEN (openssl rand -hex 32), ADMIN_CHAT_ID
docker compose up -d --build
docker compose exec app alembic upgrade head
```
