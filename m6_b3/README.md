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

## Быстрая проверка без ключа

Из каталога блока на Python 3.12+ с `uv` выполните:

```bash
uv run --locked pytest -q tests/test_agent_graph.py tests/test_agent_model.py
```

Тесты проверяют вызов инструмента, завершение по бюджету и обработку результата модели. Отдельно можно построить Mermaid-схему командой `uv run --locked python -m scripts.visualize_graph`. Файл появится в `docs/agent-graph-custom.mmd`.

Для полного набора тестов, включая оценки RAG, выполните `uv run --locked --extra eval pytest -q`.

## Запуск HTTP-сервиса

Из каталога блока создайте `.env`: `test -f .env || cp .env.example .env`. Укажите `LLM__OPENAI_API_KEY`. Модель в шаблоне уже задана как `gpt-6-luna` для агента и RAG. Для истории чатов в PostgreSQL выберите `CHAT_REPOSITORY=postgres`. Для ручек администрирования и уведомлений задайте разные случайные `ADMIN_TOKEN` и `INTERNAL_TOKEN` командой `openssl rand -hex 32`.

```bash
docker compose -f compose.yaml up -d --wait redis postgres qdrant
docker compose -f compose.yaml build app
docker compose -f compose.yaml run --rm --no-deps app alembic upgrade head
docker compose -f compose.yaml up -d --wait app
curl --fail http://localhost:8000/ready
```

Флаг `--wait` ждёт готовности контейнеров. Базовый `compose.yaml` задаёт адреса Redis, PostgreSQL и Qdrant внутри сети Docker. Если меняете `POSTGRES_PASSWORD`, согласуйте с ним `DATABASE_URL` для команд, которые запускаете вне Compose.

Для перехода между блоками сначала остановите предыдущий стек командой `docker compose -f compose.yaml down` из его каталога. У блоков общие имена контейнеров и порт 8000.

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

Агентный цикл, чат и генерация RAG используют Responses API. В `app/agents/model.py` задаётся режим рассуждения агента. Для Luna используется `none`, для Sol и Astra — `low`. Опциональный судья OpenAI также работает через Responses API. Эмбеддинги, распознавание речи и модерация используют свои API.

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
  -d '{"message":"Вызови multiply для 17 и 23 и сообщи результат."}'
```

Проверьте ответ 391 и запись `multiply` в `tool_results`. Если модель ответила напрямую, запуск инструмента проверяйте по тестам. Ответ содержит `answer` и массив `tool_results`. Этот снимок принимает только `message`, сохраняемого `thread_id` у этой ручки нет. Каждый запрос начинает граф с нового состояния. Если граф не собран, ручка возвращает 503. Результат `multiply` доступен независимо от корпуса, а поиск нужно проверить отдельным вопросом по документам.
