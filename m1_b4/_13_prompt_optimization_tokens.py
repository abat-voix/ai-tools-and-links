import tiktoken

# tiktoken — библиотека OpenAI для подсчёта токенов
# pip install tiktoken
enc = tiktoken.encoding_for_model("gpt-4")


def count_tokens(text: str) -> int:
    """Считаем количество токенов в тексте"""
    return len(enc.encode(text))


# Пример: неоптимизированный vs оптимизированный промпт
bad_prompt = """
Ты — высококвалифицированный ИИ-ассистент, который специализируется на анализе
тональности текстовых отзывов клиентов. Твоя задача — внимательно прочитать
каждый отзыв и определить его эмоциональную окраску. Ты должен классифицировать
отзыв как позитивный, негативный или нейтральный. Пожалуйста, будь внимателен
и учитывай контекст, сарказм и скрытый смысл. Ответь в формате JSON с полями
sentiment и confidence. Не добавляй лишних пояснений.
"""

good_prompt = """Классифицируй тональность отзыва: позитив/негатив/нейтрал.
Ответ — JSON: {"sentiment": "...", "confidence": 0.0-1.0}"""

print(f"Плохой промпт: {count_tokens(bad_prompt)} токенов")  # ~120 токенов
print(f"Хороший промпт: {count_tokens(good_prompt)} токенов")  # ~40 токенов
print(
    f"Экономия: {100 - count_tokens(good_prompt) / count_tokens(bad_prompt) * 100:.0f}%"
)
# Экономия: ~67%

# При 10 000 запросов/день разница:
daily_savings = (count_tokens(bad_prompt) - count_tokens(good_prompt)) * 10_000
monthly_savings_gpt5 = daily_savings * 30 * 2.50 / 1_000_000
print(f"Экономия на GPT-5.4: ~${monthly_savings_gpt5:.2f}/мес")  # ~$6/мес
