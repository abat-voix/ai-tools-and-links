# Чат-сервис на FastAPI — теперь в Docker

Образцовая реализация для блока «Docker и контейнеризация». Это снимок **одного
сквозного сервиса**: чат-ядро на FastAPI (`/chat`, `/chat/stream`, `/chat/batch`)
с кешем в Redis. На этом шаге сервис упаковывается в контейнер — одной командой
поднимается весь стек на чистой машине.

## Что нового на этом чекпоинте

Относительно предыдущего снимка (сервис жил только на локальной машине под
`uvicorn --reload`) добавлена **контейнеризация**: образ собирается в две стадии,
запускается под non-root пользователем, а `docker compose` поднимает сразу серверную
часть и Redis с автоматической проверкой состояния и зависимостью по готовности.

| Что добавилось | Файл | Зачем |
|---|---|---|
| Образ в две стадии | `Dockerfile` | сборка `builder` (зависимости через `uv`) + лёгкий `runtime` на `python:3.13-slim-bookworm` под non-root `appuser`; готовый образ ~190 MB |
| Что не кладём в образ | `.dockerignore` | держит `.env`, `.git`, `tests/`, кеши вне образа — это и секреты, и размер |
| Стек app + redis | `compose.yaml` | два сервиса: серверная часть и Redis 7.4; `depends_on: service_healthy`, общая сеть, Redis наружу не торчит |
| Удобства разработки | `compose.override.yaml` | dev-надстройка: `--reload`, монтирование `./app` внутрь, проброс Redis на хост — подмешивается автоматически |
| Готовность контейнера | `app/routers/health.py` | ручка `/ready` теперь отвечает 200/503 по состоянию Redis — на неё смотрит проверка состояния контейнера |

Мелочи того же шага: `tests/test_health.py` приведён к новому контракту `/ready`
(проверяет и 200, и 503), а в `app/core/config.py` починено имя приложения
(`app_name` стал `llm-service`). Остальное чат-ядро с прошлого шага не менялось.

## Куда смотреть

Если интересна именно контейнеризация этого чекпоинта — начинать здесь:

```
Dockerfile               # сборка в две стадии, non-root, exec-form CMD
.dockerignore            # что не попадает в образ
compose.yaml             # app + redis, проверки состояния, зависимость по готовности
compose.override.yaml    # dev-надстройка (--reload, монтирование кода)
app/routers/health.py    # /health (живость, всегда 200) и /ready (готовность, 200/503)
```

Карта всего сервиса:

```
app/        серверная часть на FastAPI: routers/ (chat, models, health),
            services/llm.py (вызовы LLM, кеш, retry), core/ (config, ошибки),
            deps/ (типизированные провайдеры), schemas/ (Pydantic-модели)
tests/      pytest + httpx.ASGITransport — без обращения к сети
```

## Как устроен образ

`Dockerfile` собирается в две стадии. Стадия `builder` ставит зависимости через
`uv sync --frozen --no-dev` с монтированием кеша и lock-файла — зависимости ставятся
**до** копирования кода, поэтому при правке `app/` пересборка занимает пару секунд.
Стадия `runtime` берёт из `builder` только готовое `/app` с виртуальным окружением,
создаёт пользователя `appuser` (uid 1000) и переключается на него — процесс внутри
контейнера работает не под root.

В образе прописан `HEALTHCHECK`, который дёргает `/ready`: контейнер считается
здоровым только когда серверная часть отвечает 200. `CMD` задан в exec-форме с
`--host 0.0.0.0`, иначе `uvicorn` слушал бы только loopback контейнера.

## Стек в compose

`compose.yaml` поднимает два сервиса:

- **`app`** — собирается из локального `Dockerfile`, публикует порт 8000, читает
  `.env`, а адрес Redis получает через `environment: REDIS_URL=redis://redis:6379/0`.
  Здесь `redis` — это DNS-имя сервиса во внутренней сети compose, **не** `localhost`.
  Сервис стартует только после того, как Redis прошёл проверку
  (`depends_on: { redis: { condition: service_healthy } }`).
- **`redis`** — образ `redis:7.4-alpine` с явным тегом, данные в именованном томе
  `redis_data`. Портов наружу нет: к Redis ходит только серверная часть по внутренней
  сети.

`compose.override.yaml` подмешивается автоматически при `docker compose up` в режиме
разработки: добавляет `--reload`, монтирует `./app` внутрь контейнера (правки кода
видны без пересборки) и пробрасывает порт Redis на хост, чтобы можно было
подключиться `redis-cli`. В проде override не выкладывается — работает только
`compose.yaml`.

## Живость и готовность

Две ручки проверки состояния различаются по смыслу:

- **`/health`** — проверка живости, всегда `200 {"status":"ok"}`. Отвечает, пока жив
  процесс, и не зависит от внешних сервисов: даже если Redis недоступен, ручка вернёт
  200. Это нужно, чтобы оркестратор не убивал контейнер из-за временно лежащего Redis.
- **`/ready`** — проверка готовности, делает `redis.ping()` с таймаутом 1.5 секунды:
  - `200 {"status":"ok","redis":"up"}`, если Redis доступен;
  - `503 {"status":"degraded","redis":"down"}`, если ping упал по таймауту или ошибке.

На `/ready` смотрят и `HEALTHCHECK` в `Dockerfile`, и проверка состояния в
`compose.yaml`: пока сервис не готов — контейнер не считается здоровым, и при будущем
деплое на него не пойдёт трафик.

## Быстрый старт

Весь стек одной командой — нужен только установленный Docker:

```bash
cp .env.example .env                  # вписать LLM__OPENAI_API_KEY для боевых вызовов
docker compose up -d --build
docker compose ps                     # оба сервиса healthy через ~15 секунд
```

Проверки:

```bash
curl -s http://localhost:8000/health  # 200 {"status":"ok"}
curl -s http://localhost:8000/ready   # 200 {"status":"ok","redis":"up"}
curl -s http://localhost:8000/docs    # Swagger открывается
docker compose exec app id            # uid=1000(appuser) — процесс не под root
docker compose exec redis redis-cli ping
```

Остановить:

```bash
docker compose down                   # остановить (данные Redis сохранятся в томе)
docker compose down -v                # + удалить том redis_data
```

Если временно остановить Redis (`docker compose stop redis`), `/ready` начнёт
отвечать 503, а `/health` останется 200.

## Без Docker (для разработки)

Тот же сервис можно поднять напрямую. Нужен [`uv`](https://docs.astral.sh/uv/)
(`brew install uv` или `pip install uv`); Python 3.12+ `uv` поставит сам.

```bash
uv sync
cp .env.example .env                  # вписать LLM__OPENAI_API_KEY
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs
```

Redis для локального запуска можно поднять отдельным контейнером
(`docker compose up -d redis`) или без него — тогда `/ready` будет отдавать 503.

## Размер образа

Multi-stage и slim-база сильно урезают образ. Ориентиры на 2026-05 (amd64):

| Подход | Размер |
|---|---|
| `python:3.13` + `COPY . .` + `pip` | ~1150 MB |
| `python:3.13-slim-bookworm` + `pip` | ~220 MB |
| slim + две стадии + `uv` (этот `Dockerfile`) | ~190 MB |

Если образ внезапно ~800 MB — скорее всего в него попал `.venv` или забыт
`.dockerignore`.

## Тесты

```bash
uv run pytest -q
```

Все тесты идут через `httpx.AsyncClient` + `ASGITransport` без обращения к сети —
`OPENAI_API_KEY` для прогона не нужен. `test_health.py` проверяет оба исхода `/ready`
(200 при живом Redis и 503 при упавшем `ping`).
