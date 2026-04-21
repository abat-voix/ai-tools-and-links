# pip install openai

from openai import OpenAI


# Подключаемся к Ollama вместо OpenAI — ОДНА строка отличия!
client = OpenAI(
    base_url="http://localhost:11434/v1",  # ← Ollama вместо api.openai.com
    api_key="ollama"                        # ← любое значение, Ollama не проверяет
)

response = client.chat.completions.create(
    model="qwen3:8b",
    messages=[
        {"role": "system", "content": "Ты — помощник разработчика."},
        {"role": "user", "content": "Что такое dependency injection?"}
    ],
    temperature=0.3
)

print(response.choices[0].message.content)
# Dependency Injection (DI) — паттерн проектирования, при котором
# зависимости объекта передаются извне, а не создаются внутри...

# Стриминг — тоже работает!
stream = client.chat.completions.create(
    model="gemma3:1b",
    messages=[{"role": "user", "content": "Что такое SOLID?"}],
    stream=True
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
