# Агент с сохранением состояния и подтверждением действия

Снимок продолжает одиночный граф из `m6_b3`. Добавлены чекпоинтер, пауза перед имитацией отправки письма, продолжение по решению человека и поток событий графа.

## Что добавилось

| Часть | Файл | Назначение |
|---|---|---|
| Состояние и подтверждение | `app/services/agent_persistent.py` | Подготовка письма, `interrupt`, продолжение, отдельное подтверждение каждого письма |
| Жизненный цикл | `app/main.py` | Чекпоинтер остаётся открыт через `AsyncExitStack` |
| HTTP-ручки | `app/routers/agent.py` | `/agent/chat`, `/agent/resume`, `/agent/stream` |
| Исключение таблиц чекпоинтера | `migrations/env.py` | Alembic не управляет таблицами `checkpoint*` |
| Разбор истории | `scripts/time_travel_demo.py` | Офлайн-пример двух решений с подставной моделью |

Настройка `AGENT_CHECKPOINTER` выбирает `memory`, `sqlite` либо `postgres`. В `.env.example` выбран SQLite, путь — `AGENT_SQLITE_PATH=var/agent_checkpoints.sqlite`. Compose сам не переключает его на Postgres. Для сохранения состояния SQLite при пересоздании контейнера нужен постоянный том для этого пути. Для Postgres установить `AGENT_CHECKPOINTER=postgres`, затем перезапустить приложение. Схему чекпоинтера создаёт его `setup()`, доменные таблицы создаются миграциями Alembic.

Текущая `_send_email` в `app/main.py` пишет событие в лог. Письма через SMTP или внешний API не отправляются. Сохранённое состояние графа и доменная история `/chats` имеют разные назначения и не синхронизируются автоматически.

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

Агентный цикл, чат и генерация RAG используют Responses API. В `app/agents/model.py` задаётся режим рассуждения агента. Для Luna используется `none`, для Sol и Astra — `low`. Опциональный судья OpenAI также работает через Responses API. Эмбеддинги, распознавание речи и модерация используют свои API.

Для опциональных зависимостей предусмотрены группы.

```bash
uv sync --locked --extra tracing
uv sync --locked --extra eval
```

Трейсинг включается через `PHOENIX_ENABLED=true`. Для приложения в Compose адрес сборщика уже задан как `http://phoenix:6006/v1/traces`. Чтобы увидеть трассы, запустить `docker compose -f compose.yaml up -d phoenix` и установить зависимости трейсинга в среду процесса приложения. Обычный Dockerfile ставит зависимости без extras, поэтому одна переменная не добавляет инструментаторы в контейнер.

Оценка RAGAS использует отдельного судью из `EVAL_JUDGE_PROVIDER` и `EVAL_JUDGE_MODEL`, по примеру окружения — Anthropic. Для неё нужен `ANTHROPIC_API_KEY`. Эти настройки не заменяют `LLM__DEFAULT_MODEL` агента.

`/ready` проверяет Redis. Работоспособность базы, агента и RAG подтверждается отдельными запросами и сообщениями старта. Ручки агента в этом примере не связывают пользователя с правом на `thread_id`. Для внешнего доступа потребуется авторизация этой связи.

## Пауза и продолжение

```bash
curl --fail -X POST http://localhost:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Подготовь письмо client@example.test с темой Статус и текстом Заявка принята","thread_id":"approval-1"}'
```

Если модель выбрала `send_email`, ответ содержит `status: "interrupted"`, `thread_id` и `interrupt` с данными подготовленного письма. Нужно проверить содержимое перед решением. Модель может выбрать другой путь, поэтому пауза не гарантируется одним текстом запроса.

```bash
curl --fail -X POST http://localhost:8000/agent/resume \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"approval-1","decision":true}'
```

Для отмены передать `decision: false`. При нескольких письмах возможна следующая пауза, поэтому каждый ответ проверяется по `status`. Использовать уникальный `thread_id` для независимых диалогов, иначе состояние смешается. Роль `full` существует в фабрике графа, но текущие HTTP-ручки используют политику `write-with-approve` и не принимают роль из тела запроса.

## Поток событий

```bash
curl -N -X POST http://localhost:8000/agent/stream \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"stream-1","input":{"messages":[{"role":"user","content":"Умножь 17 на 23"}]}}'
```

Контракт этой ручки отличается от `/agent/chat`. Начало передаётся в `input`, продолжение — через `resume` с тем же `thread_id`. SSE содержит `type: "update"` с именами узлов, `type: "token"` с полем `text`, а на паузе — `type: "interrupt"` с `payload`. Финальное `type: "done"` завершает текущий поток также после паузы. Оно не подтверждает окончательное выполнение действия. Клиент обязан сохранить информацию об `interrupt` и запросить решение человека. При обрыве или исключении графа поток может закончиться без `done`.

## Проверки

```bash
uv run pytest -q
uv run python -m scripts.time_travel_demo
```

Демонстрация истории использует SQLite в памяти и подставную модель. Она выполняется без настоящего вызова модели и без отправки писем. Повтор с реальным внешним действием потребует отдельной защиты от повторного выполнения эффекта после сбоя.
