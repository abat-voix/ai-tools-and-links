# m5_b6 — Оценка качества RAG: RAGAS 0.4 + трейсинг в Phoenix

Тот же `llm-service`, что рос с m3_b4 → m4_b4 → m5_b2 → m5_b3 → m5_b5, на
чекпоинте оценки качества. К корпоративному RAG из m5_b5 добавлены офлайн-оценка
через RAGAS 0.4 (метрики + кастомная метрика + генерация тестсета) и
опциональный трейсинг LlamaIndex в Phoenix. Оба пути — eval-time: вынесены в
опциональные группы зависимостей, в проде не ставятся.

## Что нового на этом чекпоинте

| Что добавилось | Файл | Зачем |
|---|---|---|
| Метрики RAGAS 0.4 | `app/eval/metrics.py` | Пять collections-метрик + `has_citation` на `@discrete_metric`; судья через `llm_factory`, `eval_row` собирает строку оценки |
| Вход для метрик | `app/services/rag.py` | `evaluate_inputs(q)` — ответ + полные тексты найденных чанков (`retrieved_contexts`), а не усечённые `snippet` из `/rag/query` |
| Трейсинг Phoenix | `app/observability/tracing.py` | `setup_tracing` под флагом `PHOENIX_ENABLED` + `find_spec`-гейт; вызов в lifespan до сборки индекса |
| Прогон оценки | `scripts/run_eval.py` | Гонит golden dataset через RAG, пишет per-row CSV с timestamp в `tests/eval/results/` |
| Генерация тестсета | `scripts/generate_testset.py` | `RAGAS TestsetGenerator.from_llama_index` → сырой golden dataset для ручной вычитки |
| Проверка eval-путей | `scripts/verify_eval.py` | Версии + импорты ragas/tracing + опциональный live-прогон одной метрики |
| Тесты | `tests/test_eval.py`, `tests/test_tracing.py` | Сборка строки оценки и gate трейсинга — на фейках, без сети |

Подключение: метрики и трейсинг — **опциональные группы** в `pyproject.toml`
(`eval` и `tracing`), ставятся по требованию (`uv sync --extra eval --extra
tracing`). Трейсинг включается флагом `PHOENIX_ENABLED=true`; без флага и без
пакетов сервис поднимается без спанов. Судья метрик (`claude-sonnet-4-6`)
отделён от production-LLM в `/rag/query` — это разные роли.

## Куда смотреть

Главное в этом снимке — `app/eval/metrics.py` (метрики RAGAS 0.4 и `eval_row`)
и `scripts/run_eval.py` (прогон по golden dataset). Трейсинг —
`app/observability/tracing.py` + вызов в `app/main.py` (lifespan). Всё остальное
— то же ядро, что в m5_b5.

## Карта сервиса (что выросло)

```
app/
├── eval/
│   └── metrics.py          # NEW: RAGAS 0.4 — build_judge/build_metrics/
│                           #      make_has_citation/eval_row
├── observability/
│   └── tracing.py          # NEW: Phoenix-трейсинг под флагом + find_spec-гейт
└── services/
    └── rag.py              # +evaluate_inputs(): полные retrieved_contexts для метрик
scripts/
├── run_eval.py             # NEW: прогон метрик по golden dataset → CSV
├── generate_testset.py     # NEW: RAGAS TestsetGenerator
└── verify_eval.py          # NEW: версии + импорты eval/tracing
tests/
├── test_eval.py            # NEW: eval_row + has_citation на фейках
└── test_tracing.py         # NEW: gate трейсинга (выкл / нет пакетов → False)
```

## Быстрый старт

При первом запуске скопируйте `.env.example` в `.env` и укажите
`LLM__OPENAI_API_KEY`. Для оценки дополнительно настройте судью,
например задайте `ANTHROPIC_API_KEY` для конфигурации по умолчанию.

Чат и RAG вызывают OpenAI Responses API. Модель по умолчанию — `gpt-6.2-sol`.
Доступные учебные модели в `/models` — Luna, Sol и Astra. Для генерации
тестового набора и оценки используются `EVAL_JUDGE_PROVIDER` и
`EVAL_JUDGE_MODEL`. При выборе OpenAI задайте, например, `gpt-6.2-sol`.
В обоих вариантах векторы создаёт OpenAI Embeddings API.

**Серверная часть на компьютере** с Redis и Qdrant в Docker.
В `.env` оставьте `CHAT_REPOSITORY=json` либо подключите свой PostgreSQL.

```bash
docker compose up -d redis qdrant
uv sync --locked
uv run --locked uvicorn app.main:app --reload
```

Для локального трейсинга запустите сервисы так:

```bash
docker compose up -d redis qdrant phoenix
PHOENIX_ENABLED=true uv run --locked --extra tracing uvicorn app.main:app --reload
```

Если образ Phoenix недоступен, запустите Phoenix 16.3.0 на компьютере из
закреплённых зависимостей. Redis и Qdrant можно оставить в Compose.

```bash
docker compose up -d --wait redis qdrant
uv sync --locked --extra tracing
PHOENIX_HOST=127.0.0.1 uv run --locked --extra tracing phoenix serve
```

Во втором терминале запустите FastAPI с полным адресом приёма OTLP HTTP:

```bash
curl -fsS http://127.0.0.1:6006/healthz
PHOENIX_ENABLED=true \
  PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006/v1/traces \
  uv run --locked --extra tracing uvicorn app.main:app --port 8000
```

Сделайте один запрос к `/rag/query` с фактом из учебного корпуса. На
`http://127.0.0.1:6006` откройте трассу и проверьте операции поиска и генерации.

**Полный стек в Docker.** Укажите `CHAT_REPOSITORY=postgres`,
`BOT_TOKEN`, `BOT_ADMIN_IDS`, `ADMIN_CHAT_ID`, а также свои значения
`ADMIN_TOKEN` и `INTERNAL_TOKEN` в `.env`.

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

Для трейсинга в полном стеке укажите `PHOENIX_ENABLED=true` в `.env`
и пересоберите образ той же командой. Оба варианта запуска используют
порт 8000, выберите один.

## Проверить / тесты

```bash
uv run pytest -q
# Версии и импорты eval/tracing (+ live-прогон одной метрики при наличии ключей):
uv run --extra eval --extra tracing python scripts/verify_eval.py
# Генерация тестсета и прогон оценки:
uv run --extra eval python scripts/generate_testset.py --size 30
uv run --extra eval python scripts/run_eval.py --golden tests/eval/golden_dataset.json --label baseline
```

В `tests/eval/golden_dataset.json` три вычитанных вопроса по учебному корпусу.
Они нужны для быстрой проверки конвейера. Для замеров по ДЗ подготовьте
полный набор вопросов по своему корпусу.

Студенческий README снимка m5_b6. Сервис один и тот же, растёт по чекпоинтам.
