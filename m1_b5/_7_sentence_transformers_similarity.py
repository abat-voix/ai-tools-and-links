from sentence_transformers import SentenceTransformer, util
import os
from dotenv import load_dotenv

load_dotenv()

# Загрузка модели (мультиязычная, поддерживает русский)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                            token=os.getenv("HF_TOKEN"))

# Кодируем тексты → векторы
texts = [
    "Как установить Python?",
    "How to install Python?",
    "Рецепт борща с мясом",
    "Инструкция по установке Питона"
]

embeddings = model.encode(texts)
print(f"Размерность вектора: {embeddings[0].shape}")  # (384,)

# Считаем сходство между всеми парами
similarities = util.cos_sim(embeddings, embeddings)

# Показываем результаты
print("\nМатрица сходства:")
for i, text_i in enumerate(texts):
    for j, text_j in enumerate(texts):
        if i < j:
            score = similarities[i][j].item()
            emoji = "✓" if score > 0.5 else " "
            print(f"  {emoji} {score:.2f}  '{text_i[:30]}' ↔ '{text_j[:30]}'")

# Ожидаемый результат:
#   ✓ 0.89  'Как установить Python?' ↔ 'How to install Python?'
#   ✓ 0.82  'Как установить Python?' ↔ 'Инструкция по установке Питон'
#     0.08  'Как установить Python?' ↔ 'Рецепт борща с мясом'
#   ✓ 0.78  'How to install Python?' ↔ 'Инструкция по установке Питон'
#     0.05  'How to install Python?' ↔ 'Рецепт борща с мясом'
#     0.03  'Рецепт борща с мясом' ↔ 'Инструкция по установке Питон'