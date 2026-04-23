from openai import OpenAI
import os
import time
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# список моделей (fallback цепочка)
MODELS = [
    "openai/gpt-oss-120b:free",
    # "tencent/hy3-preview:free",
]

def ask_model(prompt, max_retries=2):
    for model in MODELS:
        for attempt in range(max_retries):
            try:
                print(f"Trying {model} (attempt {attempt+1})")

                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )

                return response.choices[0].message.content

            except Exception as e:
                print(f"Error with {model}: {e}")
                time.sleep(2 ** attempt)  # exponential backoff

        print(f"Switching model...\n")

    raise Exception("Все модели недоступны 😢")


# вызов
answer = ask_model("Привет!")
print(answer)