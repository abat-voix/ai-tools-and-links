import ollama


def test_temperature(model: str, prompt: str, temperatures: list):
    """Смотрим, как температура влияет на ответ"""
    for temp in temperatures:
        responses = []
        for _ in range(3):  # 3 прогона при одной температуре
            resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temp}
            )
            responses.append(resp["message"]["content"][:80])  # Первые 80 символов

        # Проверяем: одинаковые ли ответы?
        unique = len(set(responses))
        print(f"\nТемпература {temp}:")
        print(f"  Уникальных ответов из 3: {unique}")
        print(f"  Первый ответ: {responses[0][:60]}...")


test_temperature(
    model="gemma3:1b",
    prompt="Назови столицу Франции",
    temperatures=[0.0, 0.5, 1.0, 1.5]
)


# Ожидаемый результат:
# Температура 0.0: Уникальных ответов из 3: 1     (всегда одинаковый)
# Температура 0.5: Уникальных ответов из 3: 1-2   (почти одинаковые)
# Температура 1.0: Уникальных ответов из 3: 2-3   (разные формулировки)
# Температура 1.5: Уникальных ответов из 3: 3     (максимальный разброс)
