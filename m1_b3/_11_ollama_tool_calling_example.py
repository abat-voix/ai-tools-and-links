import json

import ollama


# Описываем инструменты (tools), которые модель может вызывать
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Получить текущую погоду в городе",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Название города"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city"],
            },
        },
    }
]


# Ваша реализация функции (может ходить в реальный API)
def get_weather(city: str, units: str = "celsius") -> str:
    # В реальном приложении — запрос к weather API
    return json.dumps({"city": city, "temp": -2, "condition": "снег", "units": units})


# Шаг 1: отправляем запрос с описанием инструментов
response = ollama.chat(
    model="qwen3:8b",
    messages=[{"role": "user", "content": "Какая погода в Москве?"}],
    tools=tools,
)


# Шаг 2: модель решила вызвать функцию
if response["message"].get("tool_calls"):
    for tool_call in response["message"]["tool_calls"]:
        func_name = tool_call["function"]["name"]
        func_args = tool_call["function"]["arguments"]
        print(f"Модель вызывает: {func_name}({func_args})")
        # Модель вызывает: get_weather({"city": "Москва", "units": "celsius"})

        # Шаг 3: выполняем функцию
        result = get_weather(**func_args)

        # Шаг 4: отправляем результат обратно модели
        final_response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "user", "content": "Какая погода в Москве?"},
                response["message"],  # ответ с tool_call
                {"role": "tool", "content": result},  # результат функции
            ],
        )
        print(final_response["message"]["content"])
        # В Москве сейчас -2°C, идёт снег.
