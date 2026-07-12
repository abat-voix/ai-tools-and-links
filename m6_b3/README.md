# m6_b3 — Агентный слой на LangGraph поверх RAG

Тот же `llm-service`, что рос `m3_b4 → m4_b4 → m5_b2 → m5_b3 → m5_b5 → m5_b6`,
на чекпоинте агентов. К RAG-сервису из m5_b6 добавлен **агентный слой на
LangGraph 1.0**: ReAct-граф, собранный вручную из `StateGraph`, с инструментами —
калькулятор и поиск по базе знаний (тот самый RAG, обёрнутый в инструмент
агента). Ядро RAG, чат, модерация и персистентность — те же, что в m5_b6.

## Что нового на этом чекпоинте

| Что добавилось | Файл | Зачем |
|---|---|---|
| Состояние агента | `app/agents/state.py` | `AgentState`: история сообщений (редьюсер `add_messages`), счётчик итераций, накопленные результаты инструментов (`operator.add`) |
| Инструменты | `app/agents/tools.py` | `multiply` через `@tool` + фабрика `build_search_knowledge_base(search_fn)` — оборачивает RAG-сервис в инструмент агента, форматирует ответ с источниками |
| Сборка графа | `app/agents/graph.py` | `build_custom_graph` — `StateGraph` вручную (узлы `call_model` / `execute_tool` / `force_finish`, маршрутизатор, лимит 6 итераций); `build_prebuilt_graph` — тот же агент через `create_agent` из `langchain.agents` |
| Ручка агента | `app/routers/agent.py` | `POST /agent/chat` с телом `{message}` → `{answer, tool_results}` |
| Провайдер графа | `app/deps/providers.py` | `get_agent_graph` / `AgentGraphDep` — типизированный доступ к собранному графу из ручки |
| Визуализация | `scripts/visualize_graph.py` | `draw_mermaid()` кастомного графа → `docs/agent-graph-custom.mmd` (открывается в mermaid.live) |
| Тесты | `tests/test_agent_graph.py` | Цикл ReAct, лимит итераций (`force_finish`), неизвестный инструмент без падения, RAG-инструмент — на фейках, без сети |

Подключение: при старте приложения (`lifespan`) собирается модель
`ChatOpenAI(default_model)` и список инструментов `[multiply,
build_search_knowledge_base(...)]`, где поиск по базе знаний вызывает
RAG-сервис (`rag_service.answer`) и мягко деградирует, если RAG недоступен.
`build_custom_graph` компилирует граф в `app.state.agent_graph`, ручка
`/agent/chat` достаёт его через `AgentGraphDep`. Модель по умолчанию —
`gpt-5.4-mini`.

## Куда смотреть

Главное в этом снимке — `app/agents/graph.py` (обе сборки: вручную и через
`create_agent`) и `app/agents/tools.py` (RAG, обёрнутый в инструмент агента).
Ручка — `app/routers/agent.py`, подключение — `app/main.py` (`lifespan`). Всё
остальное — то же ядро RAG, что в m5_b6.

## Карта сервиса (что выросло)

```
app/
├── agents/                 # NEW: агентный слой LangGraph
│   ├── state.py            #   AgentState — messages(+add_messages) + счётчики
│   ├── tools.py            #   multiply (@tool) + build_search_knowledge_base — RAG как инструмент
│   └── graph.py            #   build_custom_graph (StateGraph вручную) + build_prebuilt_graph (create_agent)
├── routers/
│   └── agent.py            # NEW: POST /agent/chat — прогон графа по одному сообщению
├── deps/providers.py       # +get_agent_graph / AgentGraphDep
└── main.py                 # lifespan: сборка графа с инструментами → app.state.agent_graph
scripts/
└── visualize_graph.py      # NEW: draw_mermaid() → docs/agent-graph-custom.mmd
docs/
└── agent-graph-custom.mmd  # NEW: схема кастомного графа
tests/
└── test_agent_graph.py     # NEW: 4 теста на фейках
```

## Быстрый старт

```bash
uv sync                              # зависимости (+ langgraph, langchain, langchain-openai)
cp .env.example .env                 # подставить LLM__OPENAI_API_KEY
docker compose up -d                 # app + redis + postgres + qdrant
uv run uvicorn app.main:app --reload
```

Пример запроса к агенту:

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Сколько будет 17 умножить на 23?"}'
# {"answer": "17 × 23 = 391", "tool_results": [{"name": "multiply", ...}]}
```

## Проверить / тесты

```bash
uv run pytest -q
# Схема кастомного графа → docs/agent-graph-custom.mmd (открыть в mermaid.live):
uv run python -m scripts.visualize_graph
```

Студенческий README снимка m6_b3. Сервис один и тот же, растёт по чекпоинтам.
