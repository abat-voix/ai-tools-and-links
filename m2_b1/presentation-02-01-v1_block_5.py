# Slide: Доступ к API через прокси или egress

from __future__ import annotations

import os
from typing import Any
from dotenv import load_dotenv


def build_client() -> Any:
    try:
        from openai import DefaultHttpxClient, OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    load_dotenv()
    proxy_url = os.getenv("HTTPS_PROXY")
    if not proxy_url:
        raise SystemExit(
            "Не найден HTTPS_PROXY. Задайте его в окружении, если хотите работать через прокси."
        )

    return OpenAI(http_client=DefaultHttpxClient(proxy=proxy_url))


def main() -> None:
    client = build_client()
    print(f"Клиент с прокси настроен: {client.__class__.__name__}")
    print(f"Используемый прокси: {os.getenv('HTTPS_PROXY')}")


if __name__ == "__main__":
    main()
