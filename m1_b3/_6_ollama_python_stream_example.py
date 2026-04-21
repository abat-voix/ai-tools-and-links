import ollama


# stream=True — токены приходят по одному
stream = ollama.chat(
    model="qwen3:8b",
    messages=[
        {"role": "system", "content": "Краткий ответ"},
        {"role": "user", "content": "Расскажи про FastAPI в 3 предложениях."}
    ],
    stream=True
)

# Печатаем токены по мере поступления (эффект «печатания»)
for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)
