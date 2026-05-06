# Slide: Практика: пишем код

import os


PROVIDERS = {
    "1": {
        "name": "Ollama (локальный)",
        "api_key": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen3:8b",
        "env_key": None,
    },
    "2": {
        "name": "OpenAI",
        "api_key": None,
        "base_url": None,
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "3": {
        "name": "Groq",
        "api_key": None,
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
    },
    "4": {
        "name": "OpenRouter",
        "api_key": None,
        "base_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.0-flash-001",
        "env_key": "OPENROUTER_API_KEY",
    },
}


def choose_provider() -> dict:
    print("Выберите провайдера:")
    for key, p in PROVIDERS.items():
        print(f"  {key}. {p['name']} (модель: {p['model']})")
    while True:
        choice = input("Номер провайдера: ").strip()
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print(f"Неверный выбор. Введите число от 1 до {len(PROVIDERS)}.")


def main() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    load_dotenv()

    provider = choose_provider()

    if provider["env_key"]:
        api_key = os.getenv(provider["env_key"])
        if not api_key:
            raise SystemExit(
                f"Не найден {provider['env_key']} в переменных окружения или .env"
            )
    else:
        api_key = provider["api_key"]

    client = OpenAI(
        api_key=api_key,
        base_url=provider["base_url"],
    )
    model = provider["model"]

    print(f"\nПровайдер: {provider['name']}, модель: {model}")
    messages = [
        {"role": "system", "content": "Ты - ассистент по языку Python. Отвечай только в этом направлении. Больше ничего не говори."}
    ]

    print("Введите сообщение. Для выхода используйте exit, quit или выход.")
    while True:
        user_input = input("\nВы: ").strip()
        if user_input.lower() in ("exit", "quit", "выход"):
            print("Диалог завершён.")
            break

        if not user_input:
            print("Пустой ввод пропущен.")
            continue

        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0,
        )

        print("Ассистент: ", end="")
        full_response = ""
        usage = None
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                print(delta, end="", flush=True)
                full_response += delta
            if chunk.usage:
                usage = chunk.usage
        print()  # Печатаем перевод строки после завершения ответа

        if usage:
            print(
                f"[Токены: запрос={usage.prompt_tokens}, "
                f"ответ={usage.completion_tokens}, "
                f"всего={usage.total_tokens}]"
            )

        messages.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()