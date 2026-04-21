import ollama


def chatbot(model: str = "qwen3:8b"):
    """Простой чат-бот с историей диалога."""
    print(f"Чат-бот на модели {model}. Введите 'выход' для завершения.\n")

    # История диалога — передаётся в каждом запросе
    messages = [
        {
            "role": "system",
            "content": "Ты — дружелюбный помощник разработчика. "
                       "Отвечай на русском, кратко и с примерами кода, когда уместно."
        }
    ]

    while True:
        user_input = input("Вы: ").strip()
        if user_input.lower() in ("выход", "exit", "quit"):
            print("До свидания!")
            break
        if not user_input:
            continue

        # Добавляем сообщение пользователя в историю
        messages.append({"role": "user", "content": user_input})

        # Отправляем ВСЮ историю модели (стриминг для UX)
        print("Бот: ", end="")
        full_response = ""

        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            full_response += token

        print()  # перенос строки после ответа

        # Добавляем ответ модели в историю
        messages.append({"role": "assistant", "content": full_response})

        # Ограничиваем историю (чтобы не превысить контекстное окно)
        if len(messages) > 21:  # system + 10 пар user/assistant
            messages = [messages[0]] + messages[-20:]  # сохраняем system + последние 20
            print("[Историю обрезали до последних 10 сообщений]")


# Запуск
chatbot()

# Пример диалога:
# Вы: Что такое декоратор в Python?
# Бот: Декоратор — функция, которая оборачивает другую функцию...
# Вы: Покажи пример
# Бот: ```python
#      def timer(func):
#          def wrapper(*args, **kwargs):
#              ...
