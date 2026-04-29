from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv

load_dotenv()

# Создайте токен: huggingface.co/settings/tokens
client = InferenceClient(token=os.getenv("HF_TOKEN"))

# 1. Чат с моделью (как ChatGPT, но open-source)
response = client.chat_completion(
    model="Qwen/Qwen2.5-72B-Instruct",
    messages=[
        {"role": "system", "content": "Ты — эксперт по Python. Отвечай кратко, с примерами кода."},
        {"role": "user", "content": "Как работает декоратор @property?"}
    ],
    max_tokens=300,
    temperature=0.5
)
print(response.choices[0].message.content)

# 2. Классификация (без загрузки модели!)
result = client.text_classification(
    "Отличный сервис, рекомендую!",
    model="cointegrated/rubert-tiny-sentiment-balanced"
)
print(f"Тональность: {result[0].label} ({result[0].score:.0%})")

# 3. Получение эмбеддингов
embeddings = client.feature_extraction(
    "Машинное обучение меняет мир",
    model="sentence-transformers/all-MiniLM-L6-v2"
)
print(f"Размерность эмбеддинга: {len(embeddings[0])}")  # 384