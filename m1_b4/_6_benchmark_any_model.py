from openai import OpenAI
import time
import os
from dotenv import load_dotenv

load_dotenv()

PROMPT = "Объясни паттерн Repository в Python"

def benchmark_any_model(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    """Единый бенчмарк для локальных и облачных моделей"""
    client = OpenAI(base_url=base_url, api_key=api_key)

    start = time.perf_counter()
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    ttft = None
    tokens = 0
    for chunk in stream:
        if ttft is None and chunk.choices[0].delta.content:
            ttft = time.perf_counter() - start
        if chunk.choices[0].delta.content:
            tokens += 1

    total = time.perf_counter() - start
    return {
        "model": model,
        "ttft": round(ttft, 3),
        "total": round(total, 3),
        "throughput": round(tokens / (total - ttft), 1) if total > ttft else 0
    }


# Локальная модель (Ollama)
local = benchmark_any_model(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama не требует ключ, но параметр обязателен
    model="qwen3:8b",
    prompt=PROMPT,
)


# Облачная модель (OpenAI)
cloud = benchmark_any_model(
    base_url="https://api.openai.com/v1",
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4.1-nano",
    prompt=PROMPT,
)


print(f"Локальная: TTFT={local['ttft']}s, {local['throughput']} tok/s")
print(f"Облачная:  TTFT={cloud['ttft']}s, {cloud['throughput']} tok/s")
