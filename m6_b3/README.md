# Агентный граф поверх RAG

Снимок продолжает сервис с чатами и поиском по документам. Добавлен агент на LangGraph с инструментами умножения и поиска. Граф собирается при старте и доступен через отдельную HTTP-ручку.

## Что добавилось

| Часть | Файл | Назначение |
|---|---|---|
| Состояние | `app/agents/state.py` | Сообщения, число итераций, результаты инструментов |
| Граф | `app/agents/graph.py` | Узлы вызова модели, выполнения инструментов и завершения по бюджету |
| Инструменты | `app/agents/tools.py` | `multiply` и `build_search_knowledge_base` поверх `RAGService.answer` |
| Выбор API модели | `app/agents/model.py` | Совместимые настройки модели и проверка завершённости ответа |
| HTTP-контракт | `app/routers/agent.py` | `POST /agent/chat` с `message`, ответ с `answer` и `tool_results` |

`app/main.py` создаёт модель и передаёт графу список инструментов. `app/deps/providers.py` возвращает собранный граф через типизированную зависимость. `search_knowledge_base` возвращает ответ RAG с источниками, а не один необработанный фрагмент. `build_prebuilt_graph` показывает альтернативную сборку через `langchain.agents.create_agent`.

## Запуск

Команды выполняются из этого каталога. В `.env` задать `LLM__OPENAI_API_KEY`, `LLM__DEFAULT_MODEL=gpt-6-luna`, `RAG_LLM_MODEL=gpt-6-luna`. Заменить `ADMIN_TOKEN` и `INTERNAL_TOKEN` разными случайными значениями через `openssl rand -hex 32`. Для истории в базе задать `CHAT_REPOSITORY=postgres`. Настроить `POSTGRES_PASSWORD` и согласовать с ним `DATABASE_URL` для локальных команд.

```bash
cp .env.example .env
uv sync --locked
docker compose -f compose.yaml up -d redis postgres qdrant
docker compose -f compose.yaml build app
docker compose -f compose.yaml run --rm --no-deps app alembic upgrade head
docker compose -f compose.yaml up -d app
curl --fail http://localhost:8000/health
```

Файл `.env` заполнить до запуска контейнеров. Флаг `-f compose.yaml` задаёт базовую конфигурацию без автоматического dev-override. Отдельно запущенный на хосте `uvicorn` занимает тот же порт 8000, поэтому одновременно с контейнером приложения его запускать не нужно.

При старте приложение загружает корпус из `RAG_DATA_DIR` в `RAG_COLLECTION`. Это требует Qdrant и ключа для эмбеддингов. Сбой сборки RAG виден в логах, поиск тогда возвращает сообщение о недоступной базе. Доступность арифметического инструмента не подтверждает работу поиска.

```bash
docker compose -f compose.yaml logs --tail 100 app
```

Telegram-бот включается отдельно после настройки `BOT_TOKEN`, `BOT_ADMIN_IDS`, числового `ADMIN_CHAT_ID` и общих секретов.

```bash
docker compose -f compose.yaml up -d bot
```

Бот обращается к `/chats`, а не к `/agent/chat`. Его история, окно последних сообщений, медиа и SSE продолжают обрабатываться чат-сервисом. Резюмирования истории этот снимок не добавляет. Создание engine Postgres не проверяет доступность самой базы и не включает автоматический переход на JSON. Администрирование и лимиты используют Postgres даже при `CHAT_REPOSITORY=json`.

## Модели и окружение

`app/agents/model.py` выбирает API для инструментов. С `gpt-6-luna` используется Chat Completions и `reasoning_effort="none"`. Для остальных моделей с префиксом `gpt-6` фабрика включает Responses API и параметр `reasoning`. Это настройки агентной модели, RAG-ответ и обычный чат используют собственные пути вызова.

Для опциональных зависимостей предусмотрены группы.

```bash
uv sync --locked --extra tracing
uv sync --locked --extra eval
```

Трейсинг включается через `PHOENIX_ENABLED=true`. Для приложения в Compose адрес сборщика уже задан как `http://phoenix:6006/v1/traces`. Чтобы увидеть трассы, запустить `docker compose -f compose.yaml up -d phoenix` и установить зависимости трейсинга в среду процесса приложения. Обычный Dockerfile ставит зависимости без extras, поэтому одна переменная не добавляет инструментаторы в контейнер.

Оценка RAGAS использует отдельного судью из `EVAL_JUDGE_PROVIDER` и `EVAL_JUDGE_MODEL`, по примеру окружения — Anthropic. Для неё нужен `ANTHROPIC_API_KEY`. Эти настройки не заменяют `LLM__DEFAULT_MODEL` агента.

`/ready` проверяет Redis. Работоспособность базы, агента и RAG подтверждается отдельными запросами и сообщениями старта. Ручка `/agent/chat` в этом снимке не проверяет пользовательскую авторизацию. Для внешнего доступа требуется добавить её на стороне сервера.

## Запрос к агенту

```bash
curl --fail -X POST http://localhost:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Сколько будет 17 умножить на 23?"}'
```

Ответ содержит `answer` и массив `tool_results`. Этот снимок принимает только `message`, сохраняемого `thread_id` у этой ручки нет. Каждый запрос начинает граф с нового состояния. Если граф не собран, ручка возвращает 503. Результат `multiply` доступен независимо от корпуса, а поиск нужно проверить отдельным вопросом по документам.

## Проверки и схема

```bash
uv run pytest -q
uv run python -m scripts.visualize_graph
```

Визуализация создаёт `docs/agent-graph-custom.mmd`. Тесты графа подставляют модель и поиск. Для ручного запроса к настоящему агенту нужен действующий ключ.
