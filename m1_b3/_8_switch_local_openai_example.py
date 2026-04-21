from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Конфиг: переключается через переменную окружения
# USE_LOCAL = os.getenv("USE_LOCAL", "true").lower() == "true"
USE_LOCAL = False

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if USE_LOCAL:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    model = "qwen3:8b"
else:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )
    model = "gpt-5-mini"

# Один и тот же код для обоих вариантов!
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Привет!"}]
)
print(response.choices[0].message.content)

# Запуск:
# USE_LOCAL=true python app.py   → Ollama (бесплатно)
# USE_LOCAL=false python app.py  → OpenAI (платно, но мощнее)
