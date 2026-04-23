import ollama

from m1_b4.eval_tasks import EVAL_TASKS


def evaluate_model(model: str) -> dict:
    """Прогоняем модель через набор задач и считаем accuracy"""
    passed = 0
    details = []

    for task in EVAL_TASKS:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": task["prompt"]}]
        )
        answer = response["message"]["content"]
        success = task["check"](answer)

        if success:
            passed += 1
        details.append(f"  {'✓' if success else '✗'} {task['name']}")

    accuracy = passed / len(EVAL_TASKS) * 100
    return {"model": model, "accuracy": accuracy, "details": details}


# Оценка
result = evaluate_model("qwen3:8b")
# result = evaluate_model("gemma3:1b")
print(f"\n{result['model']}: {result['accuracy']:.0f}% ({int(result['accuracy']/20)}/{len(EVAL_TASKS)})")
for detail in result["details"]:
    print(detail)


# Пример вывода:
# qwen3:1.7b: 80% (4/5)
#   ✓ Тональность
#   ✓ Код
#   ✗ Извлечение
#   ✓ Перевод
#   ✓ JSON
