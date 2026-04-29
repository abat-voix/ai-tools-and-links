import gradio as gr
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Загрузка моделей
sentiment = pipeline("sentiment-analysis",
                      model="cointegrated/rubert-tiny-sentiment-balanced",
                      token=HF_TOKEN)
embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                               token=HF_TOKEN)

# База для поиска
kb = [
    "Python — язык программирования общего назначения",
    "FastAPI — фреймворк для создания REST API",
    "Docker — инструмент контейнеризации приложений",
    "PostgreSQL — реляционная база данных",
    "Redis — кэш и брокер сообщений",
]
kb_embeddings = embedder.encode(kb, convert_to_tensor=True)

def analyze_sentiment(text):
    res = sentiment(text)[0]
    return f"{res['label']} ({res['score']:.0%})"

def semantic_search(query):
    query_emb = embedder.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, kb_embeddings)[0]
    top = scores.argsort(descending=True)[:3]
    return "\n".join([f"[{scores[i]:.2f}] {kb[i]}" for i in top])

# Интерфейс с вкладками
with gr.Blocks(title="AI Toolkit Demo") as demo:
    gr.Markdown("# AI Toolkit: тональность + поиск")

    with gr.Tab("Анализ тональности"):
        text_in = gr.Textbox(label="Текст", lines=2)
        text_out = gr.Textbox(label="Результат")
        gr.Button("Анализировать").click(analyze_sentiment, text_in, text_out)

    with gr.Tab("Семантический поиск"):
        query_in = gr.Textbox(label="Запрос", placeholder="Что ищете?")
        results_out = gr.Textbox(label="Найденные документы", lines=5)
        gr.Button("Искать").click(semantic_search, query_in, results_out)

demo.launch()