# Простой классификатор сложности на правилах
def classify_complexity(message: str) -> str:
    """
    Определяет сложность запроса.
    В продакшене замените на ML-классификатор или LLM-based роутер.
    """
    complex_patterns = [
        "проанализируй", "анализ", "контракт", "договор",
        "риски", "на страниц", "сравни", "сделай вывод",
        "подготовь отчет", "найди ошибки"
    ]
    simple_patterns = [
        "часы работы", "адрес", "телефон", "статус заказа",
        "привет", "спасибо", "как дела", "помощь"
    ]

    # Сначала проверяем явные признаки сложной задачи, чтобы
    # короткие, но содержательные запросы не ошибочно шли в simple.
    message_lower = message.lower()
    if any(pattern in message_lower for pattern in complex_patterns):
        return "complex"

    if any(pattern in message_lower for pattern in simple_patterns):
        return "simple"

    # Короткие бытовые запросы считаем простыми.
    if len(message.split()) < 6:
        return "simple"

    return "complex"


def route_request(message: str) -> str:
    """Роутинг: простые → локально, сложные → облако."""
    complexity = classify_complexity(message)

    if complexity == "simple":
        import ollama

        # Локальная модель — бесплатно, быстро
        response = ollama.chat(
            model="qwen3:8b",
            messages=[{"role": "user", "content": message}]
        )
        return f"[LOCAL] {response['message']['content']}"
    else:
        # Облачная модель — платно, но мощнее
        # from openai import AsyncOpenAI
        # client = AsyncOpenAI(
        #     api_key=os.environ["OPENAI_API_KEY"],
        # )
        return "[CLOUD] Ответ от GPT-5 mini"


# Тестируем роутинг
tests = [
    "Какие у вас часы работы?",            # → simple → LOCAL
    "Проанализируй этот контракт на 5 страниц и найди риски",  # → complex → CLOUD
]

for msg in tests:
    complexity = classify_complexity(msg)
    print(f"[{complexity.upper()}] {msg}")
