from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    api_key=OPENAI_API_KEY,
)  # Нужен API-ключ OpenAI


def calculate_embedding_cost(
    num_documents: int,
    avg_tokens_per_doc: int,
    model: str = "text-embedding-3-small",
    price_per_m: float = 0.02,  # $0.02 за 1M токенов
) -> dict:
    """Считаем стоимость создания эмбеддингов для базы документов"""
    total_tokens = num_documents * avg_tokens_per_doc
    cost = total_tokens * price_per_m / 1_000_000

    return {
        "documents": num_documents,
        "total_tokens": total_tokens,
        "cost": round(cost, 4),
        "model": model,
    }


def create_real_embedding(
    text: str,
    model: str = "text-embedding-3-small",
) -> dict:
    """Создаем реальный embedding через OpenAI API"""
    response = client.embeddings.create(
        model=model,
        input=text,
    )

    return {
        "embedding": response.data[0].embedding,
        "dimensions": len(response.data[0].embedding),
        "tokens": response.usage.total_tokens,
        "model": response.model,
    }


# Пример: корпоративная wiki — 5000 документов
wiki = calculate_embedding_cost(
    num_documents=5000,
    avg_tokens_per_doc=500,  # ~375 слов на документ
)
print(f"Эмбеддинги для 5000 документов: ${wiki['cost']}")
# $0.05 — пять центов за всю базу!

# Пример: интернет-магазин — 100 000 товаров
shop = calculate_embedding_cost(
    num_documents=100_000,
    avg_tokens_per_doc=200,  # Название + описание товара
)
print(f"Эмбеддинги для 100К товаров: ${shop['cost']}")
# $0.40 — сорок центов


if __name__ == "__main__":
    sample_text = "OpenAI делает удобные embedding-модели для semantic search."
    real_embedding = create_real_embedding(sample_text)
    print(
        "Реальный embedding:",
        f"{real_embedding['dimensions']} измерений,",
        f"{real_embedding['tokens']} токенов",
    )
