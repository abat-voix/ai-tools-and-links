import ollama
from pydantic import BaseModel, Field


class CodeReview(BaseModel):
    """Структурированный результат code review."""

    has_bugs: bool
    bugs: list[str]
    improvements: list[str]
    security_issues: list[str]
    score: int = Field(ge=1, le=10, description="Оценка качества кода от 1 до 10")

def review_code(code: str, language: str = "python") -> CodeReview:
    """Анализирует код и возвращает структурированный отчёт."""
    response = ollama.chat(
        model="qwen3:8b",
        messages=[
            {
                "role": "system",
                "content": f"Ты — senior {language} разработчик. Проведи code review. Ответ пиши на русском языке",
            },
            {
                "role": "user",
                "content": f"Проанализируй этот код:\n\n```{language}\n{code}\n```",
            },
        ],
        format=CodeReview.model_json_schema(),
    )
    return CodeReview.model_validate_json(response["message"]["content"])


# Тестируем на «плохом» коде
bad_code = """
import subprocess

def run_command(user_input):
    result = subprocess.run(user_input, shell=True, capture_output=True)
    return result.stdout.decode()

def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    cursor.execute(query)
    return cursor.fetchone()
"""

review = review_code(bad_code)

print(f"Оценка: {review.score}/10")
print(f"Есть баги: {'да' if review.has_bugs else 'нет'}")

if review.bugs:
    print("\nБаги:")
    for bug in review.bugs:
        print(f"  - {bug}")

if review.security_issues:
    print("\nУязвимости:")
    for issue in review.security_issues:
        print(f"  - {issue}")

if review.improvements:
    print("\nУлучшения:")
    for imp in review.improvements:
        print(f"  - {imp}")

# Результат:
# Оценка: 2/10
# Есть баги: да
#
# Баги:
#   - cursor не определён в области видимости функции get_user
#
# Уязвимости:
#   - Command Injection: shell=True + пользовательский ввод
#   - SQL Injection: f-string в SQL-запросе без параметризации
#
# Улучшения:
#   - Использовать subprocess.run без shell=True и с list аргументов
#   - Использовать параметризованные запросы: cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
