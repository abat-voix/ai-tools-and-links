from m1_b4._7_calculate_ai_cost import calculate_cost
# Сценарий 1: FAQ-бот стоматологической клиники
# 200 запросов/день, короткие вопросы, короткие ответы
faq_bot = calculate_cost(
    requests_per_day=200,
    avg_input_tokens=400,   # Короткий system prompt + вопрос
    avg_output_tokens=150,  # "Запись по телефону +7..."
    input_price_per_m=0.10, # GPT-4.1 Nano — достаточно для FAQ
    output_price_per_m=0.40,
    cache_ratio=0.8         # System prompt = 80% input
)
print("=== Сценарий 1: FAQ-бот стоматологической клиники ===")
print(f"FAQ-бот: ${faq_bot['total_monthly']}/мес")  # ~$0.43/мес


# Сценарий 2: RAG-система — поиск по внутренним документам
# 500 запросов/день, длинный контекст (документы)
rag_system = calculate_cost(
    requests_per_day=500,
    avg_input_tokens=4000,  # System prompt + 3-5 документов из базы
    avg_output_tokens=600,  # Развёрнутый ответ со ссылками
    input_price_per_m=0.50, # Gemini 3 Flash — хороший баланс
    output_price_per_m=3.00,
    cache_ratio=0.3         # Документы каждый раз разные, кэшируется мало
)

print("=== Сценарий 2: RAG-система — поиск по внутренним документам ===")
print(f"RAG-система: ${rag_system['total_monthly']}/мес")  # ~$49/мес


# Сценарий 3: Batch-обработка — анализ 10К отзывов
# Одноразовая задача → считаем вручную (не помесячно)
num_reviews = 10_000
input_tokens = num_reviews * 300   # 300 токенов на отзыв (system prompt + отзыв)
output_tokens = num_reviews * 100  # 100 токенов на ответ

# DeepSeek V3.2 + Batch API (-50%): $0.14/$0.21 за 1M
batch_input_cost = input_tokens * 0.14 / 1_000_000    # $0.42
batch_output_cost = output_tokens * 0.21 / 1_000_000  # $0.21
batch_total = batch_input_cost + batch_output_cost

print("=== Сценарий 3: Batch-обработка — анализ 10К отзывов ===")
print(f"Batch 10К отзывов: ${batch_total:.2f}")  # $0.63 за ВСЮ обработку
