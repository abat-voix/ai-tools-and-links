from huggingface_hub import HfApi
import os
from dotenv import load_dotenv

load_dotenv()

api = HfApi(token=os.getenv("HF_TOKEN"))

# Поиск моделей для генерации текста, отсортированных по скачиваниям
print("Топ-5 моделей для text-generation:\n")
models = api.list_models(
    pipeline_tag="text-generation",
    sort="downloads",
    limit=5
)

for model in models:
    print(f"  {model.id}")
    print(f"    Скачиваний: {model.downloads:,}")
    print(f"    Лайков: {model.likes:,}")
    print(f"    Теги: {', '.join(model.tags[:5]) if model.tags else 'нет'}")
    print()

# Получаем детальную информацию о конкретной модели
print("="*50)
print("Детали модели Qwen3-1.7B:\n")
info = api.model_info("Qwen/Qwen3-1.7B")
print(f"  ID: {info.id}")
print(f"  Автор: {info.author}")
print(f"  Скачиваний: {info.downloads:,}")
print(f"  Лицензия: {info.card_data.get('license', 'не указана') if info.card_data else 'нет данных'}")
print(f"  Теги: {', '.join(info.tags[:8]) if info.tags else 'нет'}")
print(f"  Размер: {info.safetensors.total if info.safetensors else 'неизвестно'} параметров")
