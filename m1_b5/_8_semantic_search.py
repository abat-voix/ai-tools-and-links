from sentence_transformers import SentenceTransformer, util
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                            token=os.getenv("HF_TOKEN"))

# Корпус «документов» (база знаний курса)
docs = [
    "FastAPI — Python-фреймворк для создания REST API с автодокументацией",
    "Docker контейнеризирует приложения для единообразного деплоя",
    "PostgreSQL — реляционная СУБД с поддержкой JSON и расширений",
    "pgvector — расширение PostgreSQL для хранения и поиска векторов",
    "Redis — in-memory хранилище для кэширования и очередей",
    "LangChain — фреймворк для построения цепочек вызовов LLM",
    "Ollama запускает LLM локально через простой CLI и REST API",
    "Pinecone — облачная векторная база данных для RAG-систем",
    "Telegram Bot API позволяет создавать ботов на Python через aiogram",
    "MCP (Model Context Protocol) — стандарт подключения инструментов к LLM",
]

# Кодируем корпус ОДИН РАЗ (в продакшене — сохраняем в БД)
doc_embeddings = model.encode(docs, convert_to_tensor=True)

def search(query: str, top_k: int = 3) -> list:
    """Семантический поиск по корпусу"""
    query_emb = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, doc_embeddings)[0]
    top_indices = scores.argsort(descending=True)[:top_k]
    return [(docs[i], scores[i].item()) for i in top_indices]

# Тестируем
queries = [
    "как сделать API на Python",
    "где хранить векторы для поиска",
    "как запустить нейросеть на своём компьютере",
]

for q in queries:
    print(f"\nЗапрос: «{q}»")
    results = search(q)
    for doc, score in results:
        print(f"  [{score:.2f}] {doc}")