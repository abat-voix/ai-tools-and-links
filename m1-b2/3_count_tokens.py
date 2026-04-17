import tiktoken

# модель
MODEL = "gpt-5.4"

# цены за 1M токенов
PRICING = {
    "input": 2.50,
    "output": 15.00,
    "cached": 0.50  # обычно дешевле input
}

# encoder = tiktoken.get_encoding("cl100k_base")  # tokenizer
encoder = tiktoken.encoding_for_model("gpt-5")

def count_tokens(text):
    return len(encoder.encode(text))

# пример диалога
system_prompt = "Ты ассистент поддержки"
history = "Пользователь: Где мой заказ?\nАссистент: Проверяю..."
user_query = "Когда доставят?"

input_tokens = count_tokens(system_prompt + history + user_query)
output_tokens = 200  # допустим, модель ответила на 200 токенов

# допустим 70% истории закэшировано
cached_tokens = int(input_tokens * 0.7)
new_input_tokens = input_tokens - cached_tokens

# стоимость
cost = (
    new_input_tokens / 1_000_000 * PRICING["input"] +
    cached_tokens / 1_000_000 * PRICING["cached"] +
    output_tokens / 1_000_000 * PRICING["output"]
)

print(f"Input tokens: {input_tokens}")
print(f"Cached tokens: {cached_tokens}")
print(f"New input tokens: {new_input_tokens}")
print(f"Output tokens: {output_tokens}")
print(f"Cost: ${cost:.6f}")