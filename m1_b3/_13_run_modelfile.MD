# Создаём кастомную модель из Modelfile
ollama create techshop-bot -f Modelfile
# transferring model data...
# creating model layer...
# success

# Запускаем
ollama run techshop-bot
# >>> Здравствуйте! Я ассистент TechShop. Чем могу помочь?

# Модель появляется в списке
ollama list
# NAME              SIZE
# techshop-bot      4.9 GB
# qwen3:8b          4.9 GB