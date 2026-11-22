# Помощник техподдержки на FastAPI

Учебный HTTP-сервис вызывает OpenAI через Responses API, проверяет запросы,
поддерживает потоковую выдачу и кеширует ответы по запросу. Для базы использованы
структура FastAPI, ASGI-тесты и Redis из снимка `ai-tools-and-links/m3_b5`.

## Запуск

Нужны Python 3.12, uv и ключ OpenAI. Скопируйте `.env.example` в `.env`, заполните
`OPENAI_API_KEY` и задайте разные случайные `DEMO_TOKEN_A` и `DEMO_TOKEN_B`.

```bash
uv sync
uv run uvicorn app.main:app
```

В OpenAPI на `http://127.0.0.1:8000/docs` укажите учебный bearer-токен. Пример
тела для `POST /chat`:

```json
{"messages":[{"role":"user","content":"Как восстановить пароль в SaaS?"}]}
```

`POST /chat/stream` принимает то же тело и передаёт SSE-события
`delta`, `usage`, `done` либо `error`. Для непотокового запроса `cache: true`
включает кеш ответов, если настроен Redis. Профили из учебных токенов имеют отдельные
ключи кеша. `GET /health` проверяет процесс, `GET /ready` также проверяет Redis при
наличии `REDIS_URL`. Команда `docker compose up --build` запускает Redis вместе с API.

Учебные токены заменяют аутентификацию на семинаре. В прикладном сервисе личность
пользователя берётся из проверенной сессии или доверенного поставщика идентификации.

```bash
uv run ruff check .
uv run pytest -q
```

В тестах ответы API подставляются в HTTP-транспорт. Ключ и Redis не требуются.
