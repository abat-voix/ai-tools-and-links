# Practice: Проверка system prompt студента
# Оценивает промпт по чеклисту из задания блока 2.2.
#
# Использование:
#     python m2_b2/_practice.py

from __future__ import annotations

import json
import os
from typing import Any


EVALUATOR_PROMPT = """Ты — эксперт по промпт-инжинирингу. Тебе дан system prompt, написанный студентом для его дипломного проекта (ИИ-ассистент с RAG).

Оцени промпт по следующим критериям. Для каждого критерия поставь оценку: PASS (выполнено), PARTIAL (частично), FAIL (не выполнено) и дай краткий комментарий.

## Критерии оценки:

1. **Роль чётко определена** — понятно, кем является ассистент, в какой предметной области работает
2. **Есть ограничения (что НЕ делать)** — явно указано, чего модель делать не должна (выходить за рамки темы, давать советы в чужих областях и т.д.)
3. **Указан формат ответа** — есть указания по структуре, длине или стилю ответов
4. **Есть fallback для неизвестных вопросов** — описано поведение, когда модель не знает ответа (не выдумывать, направить к человеку и т.д.)
5. **Защита от prompt injection** — есть инструкции игнорировать попытки изменить роль, не раскрывать system prompt
6. **Длина: 500–800 токенов** — промпт достаточно подробный, но не раздутый

## Дополнительно оцени:

7. **Конкретность** — промпт написан под конкретную задачу (не generic «ты полезный ассистент»)
8. **Пригодность для production** — можно ли этот промпт использовать в реальном приложении

## Формат ответа:

Верни JSON (без markdown-обёртки) со следующей структурой:
{
  "criteria": [
    {"name": "Роль определена", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Ограничения", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Формат ответа", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Fallback", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Защита от injection", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Длина промпта", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Конкретность", "score": "PASS|PARTIAL|FAIL", "comment": "..."},
    {"name": "Production-ready", "score": "PASS|PARTIAL|FAIL", "comment": "..."}
  ],
  "total_score": "N/8",
  "summary": "Общий вывод в 2-3 предложениях",
  "recommendations": ["рекомендация 1", "рекомендация 2", "..."]
}

Считай PASS = 1 балл, PARTIAL = 0.5, FAIL = 0. Итого максимум 8/8.
""".strip()


def build_client() -> Any:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Не найден OPENAI_API_KEY в переменных окружения или .env")

    return OpenAI()


def count_tokens_approx(text: str) -> int:
    """Приблизительный подсчёт токенов (1 токен ~ 3 символа для русского текста)."""
    return len(text) // 3


def evaluate_prompt(client: Any, student_prompt: str) -> dict:
    """Отправляет промпт студента на оценку через LLM."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EVALUATOR_PROMPT},
            {
                "role": "user",
                "content": f"Вот system prompt студента для оценки:\n\n---\n{student_prompt}\n---",
            },
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # Убираем возможную markdown-обёртку
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)


def print_results(result: dict, token_count: int) -> None:
    """Выводит результаты оценки в консоль."""
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ SYSTEM PROMPT")
    print("=" * 60)
    print(f"\nПримерная длина: ~{token_count} токенов", end="")
    if 500 <= token_count <= 800:
        print(" [OK] (в рамках 500-800)")
    elif 300 <= token_count < 500:
        print(" [WARN] (коротковат, рекомендуется 500-800)")
    elif 800 < token_count <= 1000:
        print(" [WARN] (длинноват, рекомендуется 500-800)")
    else:
        print(" [FAIL] (вне рекомендуемого диапазона 500-800)")

    print("\n" + "-" * 60)
    print("КРИТЕРИИ:")
    print("-" * 60)

    for criterion in result["criteria"]:
        print(f"  [{criterion['score']}] {criterion['name']}")
        print(f"       {criterion['comment']}")

    print("\n" + "-" * 60)
    print(f"ИТОГО: {result['total_score']}")
    print("-" * 60)
    print(f"\n{result['summary']}")

    if result.get("recommendations"):
        print("\nРекомендации:")
        for rec in result["recommendations"]:
            print(f"   - {rec}")

    print("\n" + "=" * 60)


def main() -> None:
    print("=" * 60)
    print("ПРОВЕРКА SYSTEM PROMPT СТУДЕНТА")
    print("    Блок 2.2: Промпт-инжиниринг для production")
    print("=" * 60)
    print("\nВставьте system prompt студента (завершите ввод пустой строкой):\n")

    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            lines.pop()
            break
        lines.append(line)

    student_prompt = "\n".join(lines).strip()

    if not student_prompt:
        print("Промпт пустой. Нечего проверять.")
        return

    token_count = count_tokens_approx(student_prompt)
    print(f"\nАнализирую промпт ({len(student_prompt)} символов, ~{token_count} токенов)...")

    client = build_client()

    try:
        result = evaluate_prompt(client, student_prompt)
        print_results(result, token_count)
    except json.JSONDecodeError:
        print("Ошибка: не удалось распарсить ответ модели. Попробуйте ещё раз.")
    except Exception as e:
        print(f"Ошибка: {e}")
        print("Проверьте OPENAI_API_KEY и подключение к интернету.")


if __name__ == "__main__":
    main()