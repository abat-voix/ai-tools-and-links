import gradio as gr
from transformers import pipeline
import os
from dotenv import load_dotenv

load_dotenv()

# Загружаем модель анализа тональности
classifier = pipeline("sentiment-analysis",
                       model="cointegrated/rubert-tiny-sentiment-balanced",
                       token=os.getenv("HF_TOKEN"))

def analyze(text: str) -> str:
    """Анализирует тональность и возвращает результат"""
    if not text.strip():
        return "Введите текст для анализа"

    result = classifier(text)[0]
    emoji = {"positive": "😊", "negative": "😠", "neutral": "😐"}
    return f"{emoji.get(result['label'], '')} {result['label'].upper()} — уверенность {result['score']:.0%}"

# Создаём интерфейс
demo = gr.Interface(
    fn=analyze,
    inputs=gr.Textbox(label="Текст для анализа", placeholder="Напишите отзыв...", lines=3),
    outputs=gr.Textbox(label="Результат"),
    title="Анализ тональности отзывов",
    description="Введите отзыв на русском языке — модель определит его тональность",
    examples=[
        ["Отличный товар, доставили за 2 дня!"],
        ["Ужасное обслуживание, больше не приду"],
        ["Нормально, ничего особенного"],
    ]
)

demo.launch()  # Откроется http://localhost:7860
# demo.launch(share=True)  # + публичная ссылка (на 72 часа)