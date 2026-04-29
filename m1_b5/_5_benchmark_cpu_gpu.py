from transformers import pipeline
import time
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

def benchmark_device(model_name: str, prompt: str, device: str):
    """Сравниваем скорость на CPU и GPU"""
    pipe = pipeline("text-generation", model=model_name, device=device, token=HF_TOKEN)

    # Прогрев
    pipe(prompt, max_new_tokens=10)

    # Замер
    start = time.perf_counter()
    result = pipe(prompt, max_new_tokens=100, do_sample=False)
    elapsed = time.perf_counter() - start

    return {"device": device, "time": round(elapsed, 2), "tok_per_sec": round(100 / elapsed, 1)}

model = "HuggingFaceTB/SmolLM2-360M-Instruct"  # Маленькая модель для теста
prompt = "Напиши 5 советов для начинающего Python-разработчика:"

cpu = benchmark_device(model, prompt, "cpu")
print(f"CPU: {cpu['time']}s, {cpu['tok_per_sec']} tok/s")

# Если есть GPU:
# gpu = benchmark_device(model, prompt, "cuda:0")
# print(f"GPU: {gpu['time']}s, {gpu['tok_per_sec']} tok/s")