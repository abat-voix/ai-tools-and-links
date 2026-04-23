import json
import time

import ollama

from m1_b4.eval_tasks import EVAL_TASKS


def model_selection_pipeline(
    models: list,
    eval_tasks: list,
    speed_prompt: str,
    budget_per_month: float,  # Бюджет в долларах
    requests_per_day: int,
    avg_input: int,
    avg_output: int,
):
    """Полный pipeline: eval → benchmark → cost → рекомендация"""
    candidates = []

    for m in models:
        print(f"\n{'=' * 40}\nТестирую: {m['name']}...")

        # 1. Quality eval
        passed = 0
        for task in eval_tasks:
            resp = ollama.chat(
                model=m["ollama_model"],
                messages=[{"role": "user", "content": task["prompt"]}],
            )
            if task["check"](resp["message"]["content"]):
                passed += 1
        accuracy = passed / len(eval_tasks) * 100

        # 2. Speed benchmark
        start = time.perf_counter()
        stream = ollama.chat(
            model=m["ollama_model"],
            messages=[{"role": "user", "content": speed_prompt}],
            stream=True,
        )
        ttft = None
        tokens = 0
        for chunk in stream:
            if ttft is None:
                ttft = time.perf_counter() - start
            tokens += 1
        total = time.perf_counter() - start

        # 3. Cost calculation (облачная цена модели)
        monthly_cost = (
            requests_per_day * 30 * avg_input * m["input_price"] / 1_000_000
            + requests_per_day * 30 * avg_output * m["output_price"] / 1_000_000
        )

        fits_budget = monthly_cost <= budget_per_month

        candidates.append(
            {
                "name": m["name"],
                "accuracy": accuracy,
                "ttft": round(ttft, 3) if ttft else None,
                "throughput": (
                    round(tokens / (total - ttft), 1) if ttft and total > ttft else 0
                ),
                "monthly_cost": round(monthly_cost, 2),
                "fits_budget": fits_budget,
                "verdict": "✓" if fits_budget and accuracy >= 80 else "✗",
            }
        )

    # Рекомендация: самая дешёвая модель с accuracy >= 80% в рамках бюджета
    viable = [c for c in candidates if c["fits_budget"] and c["accuracy"] >= 80]
    viable.sort(key=lambda x: x["monthly_cost"])

    print(f"\n{'=' * 50}")
    print(
        f"{'Модель':20s} | {'Качество':>8s} | {'TTFT':>6s} | {'$/мес':>8s} | {'ОК':>3s}"
    )
    print(f"{'-' * 50}")
    for c in candidates:
        print(
            f"{c['name']:20s} | {c['accuracy']:>7.0f}% | {c['ttft']:>5.3f}s | "
            f"${c['monthly_cost']:>7.2f} | {c['verdict']}"
        )

    if viable:
        print(
            f"\n→ Рекомендация: {viable[0]['name']} "
            f"(${viable[0]['monthly_cost']}/мес, {viable[0]['accuracy']:.0f}% accuracy)"
        )


# Пример моделей (локальные Ollama-версии для тестирования, облачные цены для расчёта)
models_to_test = [
    {
        "name": "GPT-4.1 Nano",
        "ollama_model": "qwen3:8b",
        "input_price": 0.10,
        "output_price": 0.40,
    },
    {
        "name": "Gemini 3 Flash",
        "ollama_model": "gemma3:1b",
        "input_price": 0.50,
        "output_price": 3.00,
    },
]

model_selection_pipeline(
    models=models_to_test,
    eval_tasks=EVAL_TASKS,
    speed_prompt="Напиши функцию на Python для валидации email",
    budget_per_month=50.0,
    requests_per_day=1000,
    avg_input=800,
    avg_output=400,
)
