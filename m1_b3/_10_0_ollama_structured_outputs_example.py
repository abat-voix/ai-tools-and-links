# pip install ollama pydantic

import ollama
from pydantic import BaseModel


# Описываем структуру ответа через Pydantic
class MovieReview(BaseModel):
    title: str             # название фильма
    sentiment: str        # тональность: positive, negative или neutral
    score: float           # оценка от 0 до 10
    key_points: list[str]  # ключевые плюсы/минусы


# Запрос с format=MovieReview
response = ollama.chat(
    model="qwen3:8b",
    messages=[{
        "role": "user",
        "content": "Проанализируй отзыв: 'Фильм Дюна 2 — визуальный шедевр. "
                   "Операторская работа потрясающая, но сюжет затянут в середине.'"
    }],
    format=MovieReview.model_json_schema()  # ← магия: JSON Schema из Pydantic
)

# Парсим ответ в Pydantic-объект
review = MovieReview.model_validate_json(response["message"]["content"])

print(f"Фильм: {review.title}")
print(f"Тональность: {review.sentiment}")
print(f"Оценка: {review.score}/10")
print("Ключевые моменты:")
for point in review.key_points:
    print(f"  - {point}")

# Результат:
# Фильм: Дюна 2
# Тональность: positive
# Оценка: 8.5/10
# Ключевые моменты:
#   - Потрясающая операторская работа
#   - Визуальный шедевр
#   - Затянутый сюжет в середине
