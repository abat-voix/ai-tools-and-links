# Чат-сервис с историей и Telegram-ботом

Снимок продолжает HTTP-сервис с моделью. История и выбор контекста находятся на сервере, Telegram-бот обращается к `/chats` и показывает поток ответа.

## Что добавилось

| Возможность | Где смотреть | Назначение |
|---|---|---|
| История и контекст | `app/chat/service.py`, `app/chat/repositories/` | Сообщения в Postgres или JSON, последние `CHAT_CONTEXT_WINDOW` сообщений в контексте |
| Telegram-клиент | `bot/handlers/`, `bot/services/backend_client.py` | Текст и медиа передаются серверу, SSE отображается пользователю |
| Модерация и лимит | `app/moderation/`, `app/ratelimit/` | Проверки ввода до открытия потока |
| Администрирование | `app/admin/routes.py` | Статистика, экспорт, передача оператору, рассылка и оповещения |
| Медиа | `app/chat/media.py` | Изображение, документ, распознавание голоса через `gpt-transcribe` и FFmpeg |

Клиент OpenAI и соединения создаются в `app/main.py` при старте. Репозиторий выбирается явно через `CHAT_REPOSITORY`. Автоматического переключения с Postgres на JSON при сбое базы нет. JSON хранит историю в файлах, но лимиты, оценки и администрирование используют Postgres. Резюмирования старой истории в этом снимке нет, контекст ограничивается окном сообщений.

## Быстрый старт

Команды выполняются из этого каталога. Нужны Docker с Compose и `uv` для локальных проверок.

```bash
cp .env.example .env
uv sync --locked
```

В `.env` заполнить `LLM__OPENAI_API_KEY`, установить `CHAT_REPOSITORY=postgres`. Для полного стека нужны `BOT_TOKEN`, `BOT_ADMIN_IDS` и числовой `ADMIN_CHAT_ID`. Пустой `ADMIN_CHAT_ID=` удалить или заменить числом. `ADMIN_TOKEN` и `INTERNAL_TOKEN` заменить разными случайными значениями, каждое можно получить командой `openssl rand -hex 32`. Значения не выводить в общий журнал и не коммитить. Задать пароль `POSTGRES_PASSWORD`; для локальных вызовов базы согласовать с ним `DATABASE_URL`.

```bash
docker compose -f compose.yaml up -d --wait redis postgres
docker compose -f compose.yaml build app
docker compose -f compose.yaml run --rm --no-deps app alembic upgrade head
docker compose -f compose.yaml up -d --wait app
curl -fsS http://localhost:8000/ready
docker compose -f compose.yaml up -d --wait bot
docker compose -f compose.yaml ps
```

Бота запускать после заполнения его настроек. Проверка `/ready` отражает доступность Redis. Готовность Postgres и доступа к Telegram подтвердить созданием чата, диалогом через `/start` и чтением истории. Базовый Compose не публикует Redis и Postgres на хост. Запуск без `-f compose.yaml` автоматически применит `compose.override.yaml`, добавит перезагрузку кода и опубликованный порт Redis. Для локального запуска приложения через `uv run uvicorn app.main:app --reload` нужна отдельно доступная база с миграциями и правильные адреса зависимостей в `.env`.

`LLM__DEFAULT_MODEL=gpt-6-luna` — модель обычного чата. Генерация идёт через Responses API. `app/services/request_options.py` собирает параметры модели, а `app/services/response_stream.py` преобразует события OpenAI в поток сервиса.

## Сообщение и поток

```bash
curl --fail -X POST http://localhost:8000/chats \
  -H 'Content-Type: application/json' \
  -d '{"owner_external_id":"u-42","interface":"telegram"}'
```

Подставить полученный `chat_id` в следующий запрос.

```bash
curl -N -X POST 'http://localhost:8000/chats/<chat_id>/messages' \
  -H 'X-Owner-External-Id: u-42' \
  -F 'content=Объясни, как обратиться в поддержку'
```

Успешный поток содержит JSON в SSE-полях `data`.

```text
data: {"type":"token","delta":"..."}
data: {"type":"message_saved","message_id":"..."}
data: {"type":"done"}
```

`message_saved` появляется после сохранения ответа и даёт ID для оценки. Если генерация прерывается, сервер отправляет `{"type":"error","code":"generation_failed"}` и завершает поток без `done`. Клиент должен считать ошибкой также обрыв соединения до `done`. Блокировка модерацией и превышение лимита возвращаются до старта потока как HTTP 403/429.

`owner_external_id` и заголовок клиента служат учебными идентификаторами. Они сами по себе не подтверждают личность и не защищают доступ к чужим чатам. Для открытого сервиса требуется проверенная идентификация и проверка владельца на сервере.

## Администрирование

Ручки `/chats/admin/*` требуют `X-Admin-Token`, обратный канал бота `/notify` — `X-Internal-Token`. Их значения читаются из `.env`. Удобнее проверять административные ручки через Swagger на `http://localhost:8000/docs`, передавая настроенный секрет в поле заголовка.

`POST /chats/admin/broadcast` принимает `text` и либо `owner_ids`, либо `interface`. Рассылка идёт последовательно внутри HTTP-запроса, ответ содержит `sent` и `failed`. Фоновая очередь и устойчивое возобновление рассылки здесь не реализованы. Подтверждение оповещения через `ack` фиксирует обработку записи, но не гарантирует однократную доставку в Telegram.

Бот поддерживает `/start`, `/help`, `/clear`, `/cancel`, `/ask`, `/operator`. `/stats` и `/broadcast` доступны ID из `BOT_ADMIN_IDS`. Сервер ведёт историю, хранит оценки и статус передачи оператору. Проверку статуса перед генерацией и возобновление диалога нужно реализовать отдельно.

## Проверки

```bash
uv run --locked pytest -q
```

HTTP-клиенты подменяются в тестах, реальные сообщения в Telegram не отправляются. Проверка `/ready` показывает доступность Redis, но не подтверждает работоспособность Postgres, миграций или полного диалога. После запуска отдельно выполнить запрос к `/chats` и проверить логи.
