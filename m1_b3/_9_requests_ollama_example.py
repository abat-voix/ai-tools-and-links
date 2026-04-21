import requests
import json


# Никаких дополнительных библиотек — только requests (встроенная в Python)

def ask_ollama(prompt: str, model: str = "gemma3:1b") -> str:
    """Отправить вопрос локальной модели и получить ответ."""
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False  # получить полный ответ одним JSON
        }
    )
    return response.json()["message"]["content"]


# Использование
answer = ask_ollama("Чем list отличается от tuple в Python?")
print(answer)
# list — изменяемый (mutable), tuple — неизменяемый (immutable).
# list создаётся через [], tuple через ().
# tuple быстрее и занимает меньше памяти...


# Стриминг через requests
def stream_ollama(prompt: str, model: str = "gemma3:1b"):
    """Стриминг ответа — токены приходят по одному."""
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True  # включаем стриминг
        },
        stream=True  # requests тоже должен стримить!
    )

    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            if chunk.get("done"):
                break


stream_ollama("Напиши одно слово Работаю")
# Отступы ведут путь,
# Словарь хранит все ответы —
# Змейка пишет код.
