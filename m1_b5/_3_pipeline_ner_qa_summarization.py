from transformers import pipeline
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# 1. Распознавание именованных сущностей (NER)
ner = pipeline(
    "ner",
    model="Babelscape/wikineural-multilingual-ner",
    aggregation_strategy="simple",
    token=HF_TOKEN,
)

text = "Яндекс основан Аркадием Воложем в Москве в 1997 году."
entities = ner(text)

print("NER — извлечение сущностей:")
for ent in entities:
    print(f"  {ent['word']:20s} → {ent['entity_group']:5s} ({ent['score']:.0%})")

# 2. Ответы на вопросы по контексту
# В transformers 5 task="question-answering" больше не доступен в pipeline,
# поэтому показываем QA через instruction-following text-generation модель.
qa = pipeline(
    "text-generation",
    model="Qwen/Qwen3-0.6B",
    token=HF_TOKEN,
)

context = """FastAPI — современный Python-фреймворк для создания API.
Он использует type hints для автоматической валидации и генерации документации.
FastAPI работает на основе Starlette и Pydantic, поддерживает async/await."""

questions = [
    "На чем основан FastAPI?",
    "Что он использует для валидации?",
]

print("\nQA — ответы на вопросы по контексту:")
for question in questions:
    prompt = f"""Ответь на вопрос только по этому контексту.

Контекст:
{context}

Вопрос: {question}
Ответ:"""
    result = qa(
        prompt,
        max_new_tokens=64,
        do_sample=False,
        return_full_text=False,
    )
    answer = result[0]["generated_text"].strip()
    print(f"\n  Вопрос: {question}")
    print(f"  Ответ: {answer}")

# 3. Суммаризация (на английском — русских моделей мало)
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    token=HF_TOKEN,
)
article = """Scientists have discovered a new species of deep-sea fish
that can produce its own light. The fish was found at depths of over
3000 meters in the Pacific Ocean. Researchers believe this bioluminescence
helps the fish attract prey in the darkness of the deep ocean."""

summary = summarizer(article, max_length=50, min_length=20)
print(f"\n  Суммаризация: {summary[0]['summary_text']}")
