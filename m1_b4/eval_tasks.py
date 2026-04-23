# Набор задач для оценки — каждая с проверочной функцией
EVAL_TASKS = [
    {
        "name": "Тональность",
        "prompt": "Определи тональность отзыва одним словом (позитив/негатив/нейтрал): "
                  "'Ужасный сервис, ждал 40 минут, еда холодная'",
        "check": lambda r: "негатив" in r.lower()
    },
    {
        "name": "Код",
        "prompt": "Напиши функцию на Python: def add(a, b) -> int, которая складывает два числа",
        "check": lambda r: "def add" in r and "return" in r
    },
    {
        "name": "Извлечение",
        "prompt": "Извлеки email из текста: 'Пишите мне на info@example.com для связи'",
        "check": lambda r: "info@example.com" in r
    },
    {
        "name": "Перевод",
        "prompt": "Переведи на английский: 'Машинное обучение меняет мир'",
        "check": lambda r: "machine learning" in r.lower()
    },
    {
        "name": "JSON",
        "prompt": "Верни JSON с полями name и age для: Анна, 25 лет. Только JSON, без пояснений.",
        "check": lambda r: '"name"' in r and '"age"' in r
    },
]
