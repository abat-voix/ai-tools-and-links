import time
import ollama
import json

from m1_b4.eval_tasks import EVAL_TASKS


def full_benchmark(models: list, eval_tasks: list, prompt_speed: str, runs: int = 3):
    """Комплексный бенчмарк: скорость + качество"""
    results = []

    for model in models:
        print(f"\nТестирую {model}...")

        # 1. Замер скорости
        ttfts, throughputs = [], []
        for _ in range(runs):
            start = time.perf_counter()
            stream = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt_speed}],
                stream=True,
            )
            ttft = None
            tokens = 0
            for chunk in stream:
                if ttft is None:
                    ttft = time.perf_counter() - start
                tokens += 1
            total = time.perf_counter() - start
            ttfts.append(ttft)
            throughputs.append(tokens / (total - ttft) if total > ttft else 0)

        # 2. Оценка качества
        passed = 0
        for task in eval_tasks:
            resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": task["prompt"]}],
            )
            if task["check"](resp["message"]["content"]):
                passed += 1

        results.append({
            "model": model,
            "avg_ttft": round(sum(ttfts) / runs, 3),
            "avg_throughput": round(sum(throughputs) / runs, 1),
            "accuracy": round(passed / len(eval_tasks) * 100, 1),
            "score": round(passed / len(eval_tasks) * 100 * sum(throughputs) / runs / 100, 1),
        })

    # Сортируем по комбинированному скору
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# Запуск
results = full_benchmark(
    models=["qwen3:8b", "gemma3:1b"],
    eval_tasks=EVAL_TASKS,
    prompt_speed="Напиши REST API эндпоинт на FastAPI для списка пользователей",
)


# Красивый вывод
print("\n" + "=" * 65)
print(f"{'Модель':20s} | {'TTFT':>6s} | {'tok/s':>6s} | {'Качество':>8s} | {'Скор':>5s}")
print("-" * 65)
for r in results:
    print(
        f"{r['model']:20s} | {r['avg_ttft']:>5.3f}s | {r['avg_throughput']:>5.1f} | "
        f"{r['accuracy']:>7.1f}% | {r['score']:>5.1f}"
    )
