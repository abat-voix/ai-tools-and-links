import ollama

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

cloud_client = OpenAI(
    api_key=OPENAI_API_KEY,
)  # Для облачных моделей

SYSTEM_PROMPT = """Ты — ИИ-ассистент стоматологической клиники "Белая улыбка".

Информация о клинике:
- Адрес: Москва, ул. Примерная, д. 1
- Часы работы: ПН-ПТ 9:00-20:00, СБ 10:00-16:00
- Осмотр: 1500 рублей
- Профессиональная чистка: 5000 рублей
- Пломба: 3500 рублей
- Имплантация: от 45000 рублей

Правила ответа:
- Отвечай только по теме стоматологии и услуг клиники
- Если вопрос сложный медицинский, рекомендуй консультацию у врача
- Не выдумывай факты, которых нет в контексте
- Пиши кратко, понятно и дружелюбно
"""


def classify_complexity(question: str) -> str:
    """Определяем сложность запроса — дёшево, через маленькую модель"""
    response = ollama.chat(
        model="gemma3:1b",  # Бесплатная локальная модель
        messages=[
            {
                "role": "user",
                "content": f"Оцени сложность вопроса одним словом (простой/сложный): {question}",
            }
        ],
        options={"temperature": 0},
    )
    return response["message"]["content"].strip().lower()


def smart_route(question: str) -> str:
    """Умный роутинг: простые → дешёвая модель, сложные → дорогая"""
    complexity = classify_complexity(question)

    if "простой" in complexity:
        # Простой вопрос → GPT-4.1 Nano ($0.10/$0.40)
        response = cloud_client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        model_used = "gpt-4.1-nano ($0.10/$0.40)"
    else:
        # Сложный вопрос → GPT-5 Mini ($0.25/$2.00)
        response = cloud_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        model_used = "gpt-5-mini ($0.25/$2.00)"

    return f"[{model_used}] {response.choices[0].message.content}"


# Тест
print(smart_route("Какие часы работы клиники?"))  # → gpt-4.1-nano
print(
    smart_route("Сравни имплантацию и мостовидный протез по цене и долговечности")
)  # → gpt-5-mini
