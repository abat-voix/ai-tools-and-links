# pip install ollama tabulate

import time

import ollama


# Модели для сравнения (скачайте заранее: ollama pull <model>)
models = [
    "qwen3:8b",   # средняя
    "gemma3:1b",     # маленькая
]


# Тестовые задачи
tasks = [
    {
        "name": "Код",
        "prompt": "Напиши Python-функцию, которая находит все дубликаты в списке. "
                  "Верни только код, без объяснений."
    },
    {
        "name": "Русский текст",
        "prompt": "Объясни в 2 предложениях, чем отличается SQL от NoSQL."
    },
    {
        "name": "Анализ",
        "prompt": "Клиент написал: 'Заказ пришёл разбитый, жду возврат уже неделю!' "
                  "Определи тональность (positive/negative/neutral) и срочность (high/medium/low)."
    }
]


# Запуск бенчмарка
for model in models:
    print(f"\n{'=' * 60}")
    print(f"Модель: {model}")
    print(f"{'=' * 60}")

    for task in tasks:
        start = time.time()
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": task["prompt"]}]
        )
        elapsed = time.time() - start
        tokens = response.get("eval_count", 0)
        speed = tokens / elapsed if elapsed > 0 else 0

        # Первые 100 символов ответа
        answer_preview = response["message"]["content"][:100].replace("\n", " ")
        print(f"\n  [{task['name']}]")
        print(f"  Время: {elapsed:.1f}с | Токены: {tokens} | Скорость: {speed:.1f} tok/s")
        print(f"  Ответ: {answer_preview}...")


# Пример результата (MacBook M3 16 ГБ):
#
# Модель: qwen3:1.7b
#   [Код]       Время: 2.1с | Токены: 58  | Скорость: 27.6 tok/s
#   [Русский]   Время: 1.8с | Токены: 45  | Скорость: 25.0 tok/s
#   [Анализ]    Время: 1.5с | Токены: 32  | Скорость: 21.3 tok/s
#
# Модель: qwen3:8b
#   [Код]       Время: 3.8с | Токены: 72  | Скорость: 18.9 tok/s
#   [Русский]   Время: 2.5с | Токены: 51  | Скорость: 20.4 tok/s
#   [Анализ]    Время: 2.2с | Токены: 48  | Скорость: 21.8 tok/s
