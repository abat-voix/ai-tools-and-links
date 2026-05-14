# Slide: Структура messages: три роли

def build_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Ты — ассистент техподдержки банка. "
                "Отвечай кратко и по делу. "
                "Не давай финансовых советов."
            ),
        },
        {"role": "user", "content": "Как сменить пароль?"},
        {
            "role": "assistant",
            "content": "Перейдите в Настройки -> Безопасность -> Сменить пароль.",
        },
        {"role": "user", "content": "А где найти настройки?"},
    ]


def main() -> None:
    messages = build_messages()
    print("Пример истории сообщений для chat-модели:")
    for index, message in enumerate(messages, start=1):
        print(f"{index}. {message['role']}: {message['content']}")


if __name__ == "__main__":
    main()
