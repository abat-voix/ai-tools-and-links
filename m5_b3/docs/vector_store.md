# Vector store — отчёт по ДЗ Б5.2

Заполнить шаблон после двух загрузок корпуса и проверки поиска. Значения ниже иллюстрируют учебный снимок; в отчёт подставить имя коллекции, параметры и ID из своего прогона.

## Конфигурация

- **Движок:** Qdrant `qdrant/qdrant:v1.14.0`
- **Embedding-модель:** `text-embedding-3-small` (dim=1536), выбор из ДЗ Б5.1
- **Метрика:** cosine
- **Коллекция:** `documents`
- **HNSW:** `m=16`, `ef_construct=100` — defaults Qdrant (см. обоснование ниже)
- **Размер корпуса:** _записать точный счётчик после первого и второго вызова загрузчика_

## Метрика: cosine vs dot product

Скрипт `scripts/compare_metrics.py` создаёт временные коллекции
`documents_cosine` и `documents_dot` на одних и тех же векторах,
прогоняет 5 запросов и собирает top-5.

| Запрос | top-5 cosine | top-5 dot | Совпало |
|--------|--------------|-----------|---------|
| Как вернуть деньги за подписку | `id1, id2, ...` | `id1, id2, ...` | ✓ / ✗ |
| Сбросить пароль если не приходит письмо | ... | ... | ✓ / ✗ |
| Какой rate limit на API для бесплатного плана | ... | ... | ✓ / ✗ |
| Где найти аудит-логи действий пользователей | ... | ... | ✓ / ✗ |
| Как подключить интеграцию со Slack | ... | ... | ✓ / ✗ |

**Выбранная метрика:** _COSINE / DOT_

**Почему:** _указать нормы векторов и совпадение выдачи. При равных оценках одинаковые метрики могут вернуть разные ID на границе top-K._

## Примеры фильтров

### 1. Match по строке: `category = "billing"`

```python
from qdrant_client.models import FieldCondition, Filter, MatchValue

flt = Filter(
    must=[FieldCondition(key="category", match=MatchValue(value="billing"))]
)
hits = await store.search(query_vector=qv, top_k=3, query_filter=flt)
```

**Топ-3 для запроса «Как вернуть деньги»:**
1. `id...` — `policy_refund.md` chunk 0 — _фрагмент текста_
2. `id...` — `policy_refund.md` chunk 1 — _фрагмент_
3. `id...` — `support_billing_dispute.md` chunk 0 — _фрагмент_

### 2. Range по дате: начиная с 1 апреля 2026 года

```python
from qdrant_client.models import DatetimeRange, FieldCondition, Filter

cutoff = "2026-04-01T00:00:00Z"
flt = Filter(
    must=[FieldCondition(key="created_at", range=DatetimeRange(gte=cutoff))]
)
hits = await store.search(query_vector=qv, top_k=3, query_filter=flt)
```

**Что меняется:** _записать найденные ID и `created_at` до и после добавления фильтра. Фиксированная дата позволяет повторить эксперимент на учебном корпусе._

### 3. Композитный must + must_not: только нужный тенант, без архива

```python
from qdrant_client.models import FieldCondition, Filter, MatchValue

flt = Filter(
    must=[FieldCondition(key="tenant_id", match=MatchValue(value="acme-corp"))],
    must_not=[FieldCondition(key="status", match=MatchValue(value="archived"))],
)
hits = await store.search(query_vector=qv, top_k=3, query_filter=flt)
```

**Топ-3 для запроса «политика возврата»:** _id..., id..., id..._

Поля `tenant_id` и `status` в этом фильтре показывают схему своего проекта. В учебном JSONL есть `category`, `source` и `created_at`. Ограничение `tenant_id` для проверки доступа выводится на сервере из полномочий пользователя.

## Обычный поиск и точный эталон

Для одного вектора, фильтра и `limit` сравнить обычный `query_points` и вызов с `search_params=SearchParams(exact=True)`. Записать количество строк, пересечение ID и задержку в миллисекундах. Для оценки полноты относительно эталона разделить число общих ID на число ID в точной выдаче. Пустой эталон отметить отдельно.

Путь выполнения зависит от размера коллекции и селективности фильтра. Совпадение результатов на маленьком корпусе подтверждает контрольный сценарий. Решение о настройках HNSW принимать по измерениям на рабочем объёме.

## pgvector как альтернатива (опционально)

_Заполнить после дополнительного опыта из 5.2. Использовать одинаковые запросы и фильтры:_

| Запрос | Qdrant p50 (мс) | pgvector p50 (мс) |
|--------|-----------------|-------------------|
| ... | ... | ... |

**Финальный выбор и почему:** _оставляю Qdrant / переезжаю на pgvector — обоснование._
