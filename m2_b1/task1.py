import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


PROVIDERS = {
    "1": {
        "name": "Ollama (локальный)",
        "api_key": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "gemma3:1b",
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

messages = [
    {
        "role": "system",
        "content": "ты - помощник по Python",
    }
]


def choose_provider():
    print('Выберите провайдера:')
    for provider in PROVIDERS.items():
        print(f"{provider[0]}: {provider[1]['name']} (модель: {provider[1]['model']})")
    while True:
        choice = input('Номер провайдера: ').strip()
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print(f"Неверный выбор. Введите число от 1 до {len(PROVIDERS)}.")
def build_client(api_key, provider):
    client = OpenAI(
        api_key=api_key,
        base_url=provider['base_url'],
    )

    return client

def awesome_task():
    provider = choose_provider()

    if provider['env_key']:
        api_key = os.getenv(provider['env_key'])
        if not api_key:
            raise SystemExit(f"Для провайдера '{provider['name']}' не настроен API-ключ в переменных окружения")
    else:
        api_key = provider['api_key']

    client = build_client(api_key, provider)
    model_name = provider['model']
    print(f'Провайдер: {provider["name"]}, model: {model_name}')

    while True:
        user_input = input('Введите сообщение для модели (или "exit" для выхода): ').strip()

        if user_input == "exit":
            break

        if not user_input:
            print("Пустой ввод. Пожалуйста, введите сообщение.")
            continue

        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model=model_name,
            stream=True,
            messages=messages,
            temperature=0,
            max_tokens=200,
        )

        print("Ответ модели:")
        full_response = ""
        usage = None
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                print(delta, end="", flush=True)
                full_response += delta

            if chunk.usage:
                usage = chunk.usage

        print("\n")
        print(f"Использовано токенов: запрос={usage.prompt_tokens}, ответ={usage.completion_tokens}, всего={usage.total_tokens}")

        messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
     awesome_task()
