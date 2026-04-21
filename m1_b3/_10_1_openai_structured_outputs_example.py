# pip install openai pydantic

from openai import OpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)  # использует OPENAI_API_KEY из переменных окружения


# Описываем структуру ответа через Pydantic
class MovieReview(BaseModel):
    title: str             # название фильма
    sentiment: str         # positive / negative / neutral
    score: float           # оценка от 0 до 10
    key_points: list[str]  # ключевые плюсы/минусы


completion = client.chat.completions.parse(
    model="gpt-4.1",
    messages=[
        {
            "role": "system",
            "content": "Ты анализируешь отзывы на фильмы и возвращаешь только структурированный результат.",
        },
        {
            "role": "user",
            "content": (
                "Проанализируй отзыв: 'Фильм Дюна 2 — визуальный шедевр. "
                "Операторская работа потрясающая, но сюжет затянут в середине.'"
            ),
        },
    ],
    response_format=MovieReview,
)

message = completion.choices[0].message

if message.refusal:
    print("Модель отказалась отвечать:", message.refusal)
else:
    review = message.parsed
    print(f"Фильм: {review.title}")
    print(f"Тональность: {review.sentiment}")
    print(f"Оценка: {review.score}/10")
    print("Ключевые моменты:")
    for point in review.key_points:
        print(f"  - {point}")

# Пример ожидаемого результата:
# Фильм: Дюна 2
# Тональность: positive
# Оценка: 8.5/10
# Ключевые моменты:
#   - Потрясающая операторская работа
#   - Визуальный шедевр
#   - Затянутый сюжет в середине
