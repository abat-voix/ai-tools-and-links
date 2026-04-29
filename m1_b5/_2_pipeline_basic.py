from transformers import pipeline
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Генерация текста — 3 строки!
generator = pipeline(
    "text-generation",
    model="Qwen/Qwen3-0.6B",
    token=HF_TOKEN,
)
result = generator(
    "Объясни что такое API простыми словами:",
    max_new_tokens=100,
)

print(result[0]["generated_text"])

# Анализ тональности
sentiment = pipeline(
    "sentiment-analysis",
    model="cointegrated/rubert-tiny-sentiment-balanced",
    token=HF_TOKEN,
)
reviews = [
    "Отличный сервис, быстрая доставка!",
    "Ужасное качество, не рекомендую",
    "Нормально, за свои деньги сойдёт"
]
for review in reviews:
    res = sentiment(review)[0]
    print(f"  {res['label']:>10s} ({res['score']:.0%}) — {review}")

# Пример вывода:
#   positive (97%) — Отличный сервис, быстрая доставка!
#   negative (94%) — Ужасное качество, не рекомендую
#    neutral (71%) — Нормально, за свои деньги сойдёт
