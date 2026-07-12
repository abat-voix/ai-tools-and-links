# m6_b5 — Мультиагент: супервизор (researcher + writer) поверх агента

Тот же `llm-service`, что рос `m3_b4 → m4_b4 → m5_b2 → m5_b3 → m5_b5 → m5_b6 →
m6_b3 → m6_b4`, на чекпоинте мультиагентных систем. К одиночному ReAct-агенту
добавлен **supervisor-слой**: два специализированных агента —
`researcher` (ищет факты через RAG-инструмент) и `writer` (собирает ответ с
цитированием) — под супервизором через `langgraph-supervisor`. Персистентность,
HIL, стриминг и трейсинг из m6_b4 остаются на месте.

## Что нового на этом чекпоинте

| Что добавилось | Файл | Зачем |
|---|---|---|
| Супервизор researcher + writer | `app/agents/supervisor.py` | `build_supervisor(model, search_fn)` через `create_supervisor`; researcher ищет факты (RAG-инструмент `search_knowledge_base`), writer оформляет ответ с цитированием `[1]`, `[2]` |
| Ручка мультиагента | `app/routers/agent.py` | `POST /agent/research {question}` → ответ, собранный командой агентов |
| Провайдер + сборка | `app/deps/providers.py`, `app/main.py` | supervisor собирается в `lifespan` отдельной веткой — её сбой не роняет одиночного агента |
| Тест + демо | `tests/test_supervisor.py`, `scripts/multi_agent_demo.py` | структурный тест сборки графа + live-демо потока `supervisor → researcher → writer` |
| Зависимость | `pyproject.toml` | `langgraph-supervisor` |

Подключение: супервизор использует ту же модель и тот же RAG-инструмент, что и
одиночный агент. `create_supervisor` сам создаёт handoff-инструменты
`transfer_to_<name>` и ведёт общее состояние `messages`; researcher и writer —
это `create_agent`-подграфы. Ручная альтернатива — свой супервизор через
`Command(goto=..., update=...)` (даёт больше контроля над контекстом).

## Куда смотреть

Главное в этом снимке — `app/agents/supervisor.py` (сборка супервизора) и
`app/routers/agent.py` (`/agent/research`). Живой прогон потока —
`scripts/multi_agent_demo.py`. Всё остальное — то же ядро (RAG + персистентный
агент + HIL), что в m6_b4.

## Карта сервиса (что выросло)

```
app/
├── agents/
│   └── supervisor.py       # NEW: build_supervisor (create_supervisor: researcher + writer)
├── routers/
│   └── agent.py            # +POST /agent/research
├── deps/providers.py       # +get_supervisor / SupervisorDep
└── main.py                 # сборка supervisor в lifespan (отдельная ветка)
scripts/
└── multi_agent_demo.py     # NEW: live-демо потока супервизора
tests/
└── test_supervisor.py      # NEW: структурный тест сборки графа
```

## Быстрый старт

```bash
uv sync                              # + langgraph-supervisor
cp .env.example .env                 # LLM__OPENAI_API_KEY
docker compose up -d                 # app + postgres + qdrant + redis
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Запрос к мультиагенту:

```bash
curl -X POST localhost:8000/agent/research -H 'Content-Type: application/json' \
  -d '{"question":"Каков срок возврата денег за подписку? Ответь с источниками."}'
# researcher (RAG) собирает факты → writer оформляет ответ с цитированием [1]
```

## Проверить / тесты

```bash
uv run pytest -q
# Live-демо: supervisor → researcher → writer (нужен LLM__OPENAI_API_KEY в .env)
uv run python -m scripts.multi_agent_demo
```

Студенческий README снимка m6_b5. Сервис один и тот же, растёт по чекпоинтам.
