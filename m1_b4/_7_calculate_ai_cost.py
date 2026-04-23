def calculate_cost(
    requests_per_day: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    input_price_per_m: float,   # Цена за 1M input-токенов
    output_price_per_m: float,  # Цена за 1M output-токенов
    cache_ratio: float = 0.0,   # Доля кэшированных input-токенов (0.0–1.0)
    cache_discount: float = 0.9 # Скидка на кэшированные токены (0.9 = 90%)
) -> dict:
    """Калькулятор стоимости ИИ-проекта"""
    days_in_month = 30

    # Общее количество токенов в месяц
    total_input = requests_per_day * avg_input_tokens * days_in_month
    total_output = requests_per_day * avg_output_tokens * days_in_month

    # Стоимость input с учётом кэширования
    cached_input = total_input * cache_ratio
    uncached_input = total_input * (1 - cache_ratio)
    input_cost = (
        uncached_input * input_price_per_m / 1_000_000 +
        cached_input * input_price_per_m * (1 - cache_discount) / 1_000_000
    )

    # Стоимость output (не кэшируется)
    output_cost = total_output * output_price_per_m / 1_000_000

    total = input_cost + output_cost

    return {
        "requests_month": requests_per_day * days_in_month,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "input_cost": round(input_cost, 2),
        "output_cost": round(output_cost, 2),
        "total_monthly": round(total, 2),
        "cost_per_request": round(total / (requests_per_day * days_in_month), 6)
    }


# Сценарий: чат-бот с 1000 запросов/день
chatbot = calculate_cost(
    requests_per_day=1000,
    avg_input_tokens=800,   # system prompt + вопрос пользователя
    avg_output_tokens=400,  # ответ модели
    input_price_per_m=0.28, # DeepSeek V3.2
    output_price_per_m=0.42,
    cache_ratio=0.7,        # 70% input — это system prompt (кэшируется)
    cache_discount=0.9      # 90% скидка на кэш у DeepSeek
)


print("Чат-бот на DeepSeek V3.2:")
print(f"  Запросов/месяц: {chatbot['requests_month']:,}")
print(f"  Input: ${chatbot['input_cost']}")
print(f"  Output: ${chatbot['output_cost']}")
print(f"  Итого: ${chatbot['total_monthly']}/месяц")
print(f"  За один запрос: ${chatbot['cost_per_request']}")
# Итого: ~$7.53/месяц за 30 000 запросов


# Один сценарий: чат-бот, 1000 запросов/день, 800 input, 400 output
providers = [
    {"name": "GPT-5.4",           "input": 2.50,  "output": 15.00, "cache_discount": 0.90},
    {"name": "GPT-5 Mini",        "input": 0.25,  "output": 2.00,  "cache_discount": 0.90},
    {"name": "GPT-4.1 Nano",      "input": 0.10,  "output": 0.40,  "cache_discount": 0.75},
    {"name": "Claude Sonnet 4.6", "input": 3.00,  "output": 15.00, "cache_discount": 0.90},
    {"name": "Claude Haiku 4.5",  "input": 1.00,  "output": 5.00,  "cache_discount": 0.90},
    {"name": "Gemini 3 Flash",    "input": 0.50,  "output": 3.00,  "cache_discount": 0.50},
    {"name": "Gemini Flash-Lite", "input": 0.10,  "output": 0.40,  "cache_discount": 0.50},
    {"name": "DeepSeek V3.2",     "input": 0.28,  "output": 0.42,  "cache_discount": 0.90},
]

print(f"{'Провайдер':25s} | {'Без кэша':>10s} | {'С кэшем 70%':>12s} | {'За запрос':>10s}")
print("-" * 65)

for p in providers:
    # Без кэша
    no_cache = calculate_cost(1000, 800, 400, p["input"], p["output"])
    # С кэшем
    with_cache = calculate_cost(1000, 800, 400, p["input"], p["output"],
                                cache_ratio=0.7, cache_discount=p["cache_discount"])
    print(f"{p['name']:25s} | ${no_cache['total_monthly']:>8.2f} | "
          f"${with_cache['total_monthly']:>10.2f} | ${with_cache['cost_per_request']:.6f}")

# Пример вывода:
# GPT-5.4                   |   $240.00 |     $202.20 | $0.006740
# GPT-5 Mini                |    $30.00 |      $26.22 | $0.000874
# GPT-4.1 Nano              |     $7.20 |       $5.94 | $0.000198
# Claude Sonnet 4.6         |   $252.00 |     $206.64 | $0.006888
# Claude Haiku 4.5          |    $84.00 |      $68.88 | $0.002296
# Gemini 3 Flash            |    $48.00 |      $43.80 | $0.001460
# Gemini Flash-Lite         |     $7.20 |       $6.36 | $0.000212
# DeepSeek V3.2             |    $11.76 |       $7.53 | $0.000251