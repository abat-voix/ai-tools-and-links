# Slide: GigaChat (Сбер): особенности подключения

import os
import uuid
from typing import Any


def main() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        import requests
    except ImportError as exc:
        raise SystemExit("Установите зависимость requests: pip install requests") from exc

    load_dotenv()
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise SystemExit("Не найден GIGACHAT_CREDENTIALS в переменных окружения или .env")

    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    auth_response = requests.post(
        auth_url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {credentials}",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        verify=False,
        timeout=30,
    )
    auth_response.raise_for_status()
    access_token = auth_response.json()["access_token"]

    response = requests.post(
        "https://gigachat.devices.sberbank.ru/api/v1",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "model": "GigaChat-Lite",
            "messages": [{"role": "user", "content": "Привет!"}],
        },
        verify=False,
        timeout=30,
    )
    response.raise_for_status()
    print(response.json()["choices"][0]["message"]["content"])


def get_gigachat_token(credentials: str) -> str:
    """Получает access_token через OAuth для GigaChat."""
    import requests

    auth_response = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {credentials}",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        verify=False,
        timeout=30,
    )
    auth_response.raise_for_status()
    return auth_response.json()["access_token"]


def main_openai() -> None:
    """GigaChat через OpenAI-совместимый клиент."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit("Установите: pip install python-dotenv") from exc

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите: pip install openai") from exc

    load_dotenv()
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise SystemExit("Не найден GIGACHAT_CREDENTIALS в переменных окружения или .env")

    access_token = get_gigachat_token(credentials)

    import httpx

    client = OpenAI(
        api_key=access_token,
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        http_client=httpx.Client(verify=False),
    )

    response = client.chat.completions.create(
        model="GigaChat",
        messages=[{"role": "user", "content": "Привет!"}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    # main()  # requests-версия
    main_openai()  # OpenAI-совместимая версия
