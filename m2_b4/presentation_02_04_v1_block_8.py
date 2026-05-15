# Slide: Инвалидация кеша — версионирование промпта

import hashlib
import json
from loguru import logger

def make_versioned_key(
    model: str, messages: list[dict], version: str = "v1"
) -> str:
    """Создаёт ключ кеша с версией промпта.

    При изменении промпта достаточно поднять версию —
    старый кеш перестанет совпадать.
    """
    data = json.dumps(
        {"model": model, "messages": messages},
        sort_keys=True,
        ensure_ascii=False,
    )
    content_hash = hashlib.sha256(data.encode()).hexdigest()[:16]
    return f"llm:{version}:{content_hash}"


def main() -> None:
    """Демонстрация версионирования ключей кеша."""
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "Что такое REST?"}]

    key_v1 = make_versioned_key(model, messages, version="v1")
    key_v2 = make_versioned_key(model, messages, version="v2")

    logger.info("Ключ v1: {}", key_v1)
    logger.info("Ключ v2: {}", key_v2)
    logger.info("Ключи совпадают: {}", key_v1 == key_v2)
    # При смене промпта → v3 → старый кеш не совпадает


if __name__ == "__main__":
    main()