import json

from openai import OpenAI

client = OpenAI()

# Шаг 1: Подготовка пакета запросов в формате JSONL
reviews = [
    "Отличный товар, доставили быстро!",
    "Ужасное качество, верну обратно",
    "Нормально, но за эти деньги ожидал большего",
    # ... ещё 9997 отзывов
]

# Создаём JSONL-файл
with open("batch_input.jsonl", "w") as f:
    for i, review in enumerate(reviews):
        request = {
            "custom_id": f"review-{i}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {
                        "role": "system",
                        "content": "Классифицируй отзыв: позитив/негатив/нейтрал. Ответь одним словом.",
                    },
                    {"role": "user", "content": review},
                ],
                "temperature": 0,
            },
        }
        f.write(json.dumps(request, ensure_ascii=False) + "\n")

# Шаг 2: Загружаем файл и запускаем batch
batch_file = client.files.create(
    file=open("batch_input.jsonl", "rb"),
    purpose="batch",
)

batch_job = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",  # Результат в течение 24 часов
)

print(f"Batch запущен: {batch_job.id}")
print(f"Статус: {batch_job.status}")  # "validating" → "in_progress" → "completed"

# Шаг 3: Проверяем статус (через несколько часов)
# status = client.batches.retrieve(batch_job.id)
# if status.status == "completed":
#     results = client.files.content(status.output_file_id)
