from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")


def get_device_and_dtype():
    if torch.cuda.is_available():
        return torch.device("cuda"), torch.float16
    if torch.backends.mps.is_available():
        return torch.device("mps"), torch.float16
    return torch.device("cpu"), torch.float32

# Загрузка модели и токенизатора
model_name = "Qwen/Qwen3-0.6B"
device, dtype = get_device_and_dtype()

tokenizer = AutoTokenizer.from_pretrained(model_name, token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=dtype,
    token=HF_TOKEN
)
model = model.to(device)
model.eval()

# Подготовка промпта
messages = [
    {"role": "system", "content": "Ты — полезный ассистент. Отвечай кратко."},
    {"role": "user", "content": "Что такое Docker?"}
]

# Применяем chat template модели (у каждой модели свой!)
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

# Токенизация: текст → числа
inputs = tokenizer(text, return_tensors="pt").to(device)
print(f"Количество input-токенов: {inputs['input_ids'].shape[1]}")
print(f"Устройство: {device}, dtype: {dtype}")

# Генерация
with torch.no_grad():  # Отключаем gradient — экономим память
    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        repetition_penalty=1.2  # Штраф за повторения
    )

# Декодирование: числа → текст
response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
print(f"Ответ: {response}")
