# pip install ollama
# poetry add ollama

import ollama


# Простой чат
response = ollama.chat(
    model="gemma3:1b",
    messages=[
        {"role": "system", "content": "Ты — опытный Python-разработчик."},
        {"role": "user", "content": "Напиши функцию для валидации email. Один простой вариант решения."},
    ]
)

print(response["message"]["content"])
# def validate_email(email: str) -> bool:
#     import re
#     pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
#     return bool(re.match(pattern, email))

# Метрики производительности
tokens = response["eval_count"]
duration_sec = response["eval_duration"] / 1e9
print(f"Токенов: {tokens}, Скорость: {tokens / duration_sec:.1f} tok/s")
# Токенов: 67, Скорость: 28.4 tok/s
