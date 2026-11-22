# Чат-сервис и поиск в Qdrant

Снимок одного растущего сервиса: серверная часть на FastAPI, тонкий Telegram-бот и хранение диалогов. На этом шаге добавляются эмбеддинги документов и поиск с фильтрами по метаданным.

## Что добавилось

| Возможность | Файл | Назначение |
|---|---|---|
| Векторное хранилище | app/services/vector_store.py | Создание коллекции, индексы, заливка и поиск |
| Клиент эмбеддингов | app/services/embeddings.py | Получение векторов текстов через OpenAI |
| Загрузка корпуса | scripts/load_to_qdrant.py | Чтение JSONL, эмбеддинги и точки Qdrant |
| Сравнение метрик | scripts/compare_metrics.py | Ранжирование COSINE и DOT на одних векторах |
| Проверка хранилища | tests/test_vector_store.py | Поиск, фильтры и размерность |

Точки получают стабильный UUID по источнику и номеру фрагмента. Повторная загрузка тех же записей обновляет их вместо создания дублей. Удаление записи из JSONL само по себе не удаляет старую точку.

## Куда смотреть

Начать с scripts/load_to_qdrant.py и app/services/vector_store.py. В data/sample_kb.jsonl лежит корпус техподдержки SaaS. app/main.py подключает хранилище при старте. Если оно недоступно, другие возможности приложения могут продолжить работу.

Для локальной проверки геометрии без API подходит [пример косинуса и порога](../m5_b1/README.md).

## Быстрый старт

Нужны Python 3.12, uv, Docker и ключ OpenAI. Команды выполняются из этого каталога. При первом запуске создать .env по .env.example и заполнить LLM__OPENAI_API_KEY. Существующий .env сохранить.

~~~bash
uv sync
cp .env.example .env
docker compose up -d qdrant
QDRANT_URL=http://localhost:6333 uv run python scripts/load_to_qdrant.py
~~~

Векторизация корпуса обращается к OpenAI. EMBEDDING_MODEL и EMBEDDING_DIM должны соответствовать друг другу. Скрипт сверяет размерность полученных векторов до записи. Коллекция с другой размерностью требует отдельного имени или явной миграции.

Повторить последнюю команду и проверить количество точек в панели Qdrant на http://localhost:6333/dashboard.

## Сравнение COSINE и DOT

~~~bash
QDRANT_URL=http://localhost:6333 uv run python scripts/compare_metrics.py
~~~

Скрипт получает настоящие эмбеддинги через API, создаёт коллекции с суффиксами _cosine и _dot и пишет docs/metric_comparison.json. Для нормализованных векторов обе метрики должны давать одинаковый порядок с учётом равных оценок. Имена этих коллекций зарезервировать для эксперимента: скрипт пересоздаёт их.

## Проверки

~~~bash
uv run pytest -q
QDRANT_TEST_URL=http://localhost:6333 uv run pytest tests/test_vector_store.py -v
~~~

QDRANT_TEST_URL включает сетевые тесты хранилища. QDRANT_URL настраивает само приложение и скрипты загрузки. Это разные настройки.

## Серверная часть и полный стек

Для локального запуска серверной части:

~~~bash
QDRANT_URL=http://localhost:6333 uv run uvicorn app.main:app --reload --port 8000
~~~

Для полного compose заполнить в .env ключ модели, BOT_TOKEN, BOT_ADMIN_IDS, ADMIN_TOKEN, INTERNAL_TOKEN и ADMIN_CHAT_ID. Токены администратора и внутренних вызовов должны быть собственными случайными значениями.

~~~bash
docker compose up -d --build
docker compose exec app alembic upgrade head
~~~

В сети compose адрес Qdrant задаётся как http://qdrant:6333. При запуске Python на компьютере используется опубликованный порт localhost.

## Сравнение с pgvector

[SQL-пример фильтрованного поиска](pgvector/README.md) сравнивает два режима HNSW и точную выдачу.
