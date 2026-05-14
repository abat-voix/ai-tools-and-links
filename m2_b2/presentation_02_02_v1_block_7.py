# Slide: Prompt templates: параметризация

from __future__ import annotations


def main() -> None:
    # Вариант 1: f-strings (простейший)
    def create_prompt(product: str, question: str) -> str:
        return f"""Ты — эксперт по {product}.
                Ответь на вопрос клиента кратко и по делу.
                Вопрос: {question}"""

    prompt = create_prompt("Python", "Как работают генераторы?")
    print("=== Вариант 1: f-strings ===\n")
    print(prompt)

    # Вариант 2: Jinja2 (для сложных шаблонов)
    try:
        from jinja2 import Template
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость jinja2: pip install jinja2"
        ) from exc

    template = Template("""Ты — ассистент техподдержки.
    {% if language == "ru" %}
    Отвечай на русском языке.
    {% else %}
    Answer in English.
    {% endif %}
    
    {% if examples %}
    Примеры ответов:
    {% for ex in examples %}
    - Вопрос: {{ ex.q }}
      Ответ: {{ ex.a }}
    {% endfor %}
    {% endif %}
    
    Вопрос клиента: {{ question }}""")

    system_prompt = template.render(
        language="en",
        examples=[
            {"q": "Как сменить пароль?", "a": "Настройки → Безопасность"},
            {"q": "Сколько стоит?", "a": "Тарифы на странице pricing."},
        ],
        question="Как подключить двухфакторную аутентификацию?"
    )

    print("\n=== Вариант 2: Jinja2 ===\n")
    print(system_prompt)


if __name__ == "__main__":
    main()