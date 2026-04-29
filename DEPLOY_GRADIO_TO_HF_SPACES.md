# Деплой Gradio-приложения на Hugging Face Spaces

## 1. Подготовка

- Зарегистрируйтесь на [huggingface.co](https://huggingface.co/join).
- Создайте [Access Token](https://huggingface.co/settings/tokens) с правами `write`.

## 2. Создание Space через веб-интерфейс

1. Перейдите на [huggingface.co/new-space](https://huggingface.co/new-space).
2. Укажите имя (например, `my-gradio-app`).
3. Выберите SDK — **Gradio**.
4. Выберите видимость: **Public** (бесплатно) или **Private**.
5. Нажмите **Create Space**.

## 3. Структура файлов

Минимально нужны два файла:

```
my-gradio-app/
├── app.py              # точка входа
└── requirements.txt    # зависимости
```

### app.py — пример

```python
import gradio as gr


def greet(name: str) -> str:
    return f"Привет, {name}!"


demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.launch()
```

### requirements.txt

```
gradio
```

Если приложение использует другие библиотеки (transformers, torch и т.д.), добавьте их сюда.

## 4. Загрузка файлов

### Вариант A — через Git

Установите CLI и авторизуйтесь (нужно сделать один раз):

```bash
pip install huggingface_hub
huggingface-cli login
```

Затем клонируйте Space и загрузите файлы:

```bash
git clone https://huggingface.co/spaces/ВАШ_ЛОГИН/my-gradio-app
cd my-gradio-app

# скопируйте app.py и requirements.txt в эту папку

git add .
git commit -m "initial commit"
git push
```

### Вариант B — через веб-интерфейс

Откройте Space → вкладка **Files** → **Add file** → загрузите `app.py` и `requirements.txt`.

### Вариант C — через Python API

```python
from huggingface_hub import HfApi

api = HfApi()
api.upload_file(
    path_or_fileobj="app.py",
    path_in_repo="app.py",
    repo_id="ВАШ_ЛОГИН/my-gradio-app",
    repo_type="space",
)
api.upload_file(
    path_or_fileobj="requirements.txt",
    path_in_repo="requirements.txt",
    repo_id="ВАШ_ЛОГИН/my-gradio-app",
    repo_type="space",
)
```

## 5. Переменные окружения (секреты)

Если приложение использует API-ключи (например, OpenAI), **не кладите их в код**.

1. Откройте Space → **Settings** → **Variables and secrets**.
2. Добавьте секрет, например `OPENAI_API_KEY`.
3. В коде читайте через `os.environ`:

```python
import os

api_key = os.environ["OPENAI_API_KEY"]
```

## 6. Настройка оборудования

По умолчанию Space работает на **CPU Basic** (2 vCPU, 16 GB RAM) — бесплатно.

Если нужен GPU (для inference моделей), в **Settings** → **Hardware** выберите нужный тариф.

## 7. Полезные настройки

В корне репозитория Space автоматически создается файл `README.md` с YAML-шапкой:

```yaml
---
title: My Gradio App
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.0"
app_file: app.py
pinned: false
---
```

- `app_file` — точка входа (по умолчанию `app.py`).
- `pinned` — закрепить Space в профиле.
- `sdk_version` — версия Gradio.

## 8. После деплоя

- Приложение доступно по адресу: `https://huggingface.co/spaces/ВАШ_ЛОГИН/my-gradio-app`
- Логи сборки и ошибки видны во вкладке **Logs**.
- Любой `git push` или загрузка файла через UI автоматически пересобирает Space.